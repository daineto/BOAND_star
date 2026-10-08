"""Durable execution records around the pinned external runner's scripts.

The generated shell command, timeout signal and memory limit are unchanged.
Completion of an execution is independent of completion of the planner search.
"""
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(file, value):
    file = Path(file)
    temporary = file.with_suffix(file.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(file)


@contextmanager
def run_lock(directory, create=True):
    """Prevent two controllers from executing the same campaign run."""
    lock = Path(directory) / ".execution.lock"
    if not create and not lock.exists():
        yield
        return
    with lock.open("a" if create else "r") as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This run already has an active execution controller") from None
        yield


def process_identity(pid):
    try:
        # The command name can contain spaces: split after its closing parenthesis.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "start_ticks": fields[19]}
    except FileNotFoundError:
        return None


def session_groups(session):
    """GNU timeout creates its own process group inside the wrapper's session."""
    groups = set()
    for file in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = file.read_text().rsplit(")", 1)[1].split()
            if int(fields[3]) == session and fields[0] != "Z":
                groups.add(int(fields[2]))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return groups


def stop_session(session):
    def send(sig):
        for group in session_groups(session):
            try:
                os.killpg(group, sig)
            except ProcessLookupError:
                pass

    send(signal.SIGTERM)
    deadline = time.monotonic() + 3
    while session_groups(session) and time.monotonic() < deadline:
        time.sleep(0.05)
    send(signal.SIGKILL)
    deadline = time.monotonic() + 3
    while session_groups(session) and time.monotonic() < deadline:
        time.sleep(0.05)
    if session_groups(session):
        raise RuntimeError(f"Job session {session} still has active processes")


def active_record(record):
    identity = record.get("process_identity")
    if identity is None or record.get("state") == "finished":
        return False
    same_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip() == identity["boot_id"]
    return same_boot and bool(session_groups(record["pid"]))


def instrument_script(script, receipt):
    """Capture os.system's real exit code, which the external wrapper discards."""
    source = Path(script).read_text()
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, ast.Expr)
               and isinstance(node.value, ast.Call)
               and isinstance(node.value.func, ast.Attribute)
               and isinstance(node.value.func.value, ast.Name)
               and node.value.func.value.id == "os" and node.value.func.attr == "system"]
    if len(matches) != 1:
        raise ValueError("Unsupported external execution script: expected one os.system command")
    call = matches[0]
    lines = source.splitlines(keepends=True)
    lines[call.lineno - 1:call.end_lineno] = [
        "_boand_exit_code = os.waitstatus_to_exitcode(" + ast.get_source_segment(source, call.value) + ")\n"]
    source = "".join(lines)
    # Written only after the wrapper's normal cleanup succeeds.
    source += f"\nwith open({str(receipt)!r}, 'x') as _boand_receipt:\n    _boand_receipt.write(str(_boand_exit_code))\n"
    Path(script).write_text(source)


def run_job(script, directory, stop):
    directory = Path(directory)
    state_file = directory / "execution.json"
    receipt = directory / "exit-code.txt"
    record = {"schema_version": 1, "state": "running", "started_at": timestamp()}
    atomic_json(state_file, record)
    process = None
    try:
        with (directory / "wrapper.log").open("xb") as output:
            process = subprocess.Popen([sys.executable, str(script)], stdout=output, stderr=output,
                                       start_new_session=True)
            record.update(pid=process.pid, process_identity=process_identity(process.pid))
            atomic_json(state_file, record)
            while process.poll() is None:
                if stop.wait(0.2):
                    stop_session(process.pid)
                    process.wait()
                    break
        record["wrapper_returncode"] = process.returncode
        if session_groups(process.pid):
            stop_session(process.pid)
        if not stop.is_set() and process.returncode == 0 and receipt.is_file():
            code = int(receipt.read_text())
            stderr = next(directory.glob("err_*.txt"), None)
            errors = stderr.read_text() if stderr else ""
            record.update(state="finished", returncode=code,
                          termination=("timeout" if code == 124 else "memory_error" if "MemoryError" in errors
                                       else "success" if code == 0 else "planner_error"))
        else:
            record.update(state="interrupted" if stop.is_set() else "infrastructure_error")
    except Exception as error:
        if process is not None:
            stop_session(process.pid)
            process.wait()
        record.update(state="infrastructure_error", error=repr(error))
    record["ended_at"] = timestamp()
    atomic_json(state_file, record)
    return record


def execute_jobs(jobs, workers, on_finished):
    stop = threading.Event()
    old_handlers = {}

    def interrupt(_signal, _frame):
        stop.set()

    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            old_handlers[sig] = signal.signal(sig, interrupt)
    finished = 0
    try:
        # Submit at most `workers` jobs, so interruption never starts queued jobs.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending = iter(jobs)
            futures = {}

            def submit():
                job = next(pending, None)
                if job is not None and not stop.is_set():
                    futures[pool.submit(run_job, job["script"], job["directory"], stop)] = job

            for _ in range(workers):
                submit()
            try:
                while futures:
                    future = next(as_completed(futures))
                    job = futures.pop(future)
                    record = future.result()
                    finished += record["state"] == "finished"
                    on_finished(job, record)
                    print(f"Execution progress: {finished}/{len(jobs)} finished; {job['key']}: {record['state']}", flush=True)
                    submit()
            except BaseException:
                stop.set()
                raise
        if stop.is_set():
            raise KeyboardInterrupt("Campaign interrupted; finished executions can be resumed")
    finally:
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
