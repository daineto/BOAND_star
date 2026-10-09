"""Build the pinned Fast Downward CPython module without editing upstream files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "outputs/fast-downward/source")
    parser.add_argument("--compiler", default="g++-12")
    parser.add_argument("--jobs", type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    source = args.source.resolve()
    pin = json.loads((HERE / "upstream.json").read_text())
    git = ["git", "-c", f"safe.directory={source}"]
    revision = subprocess.check_output([*git, "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if revision != pin["revision"]:
        parser.error(f"Expected upstream revision {pin['revision']}, got {revision}")
    if subprocess.check_output([*git, "status", "--porcelain"], cwd=source, text=True).strip():
        parser.error("Upstream checkout must be clean")
    directory = ROOT / "outputs/fast-downward"
    overlay = directory / "module-source"
    shutil.copytree(source / "src", overlay, dirs_exist_ok=True)
    cmake = overlay / "search/CMakeLists.txt"
    text = cmake.read_text()
    original = "add_executable(downward planner.cc)"
    if text.count(original) != 1:
        parser.error("Upstream CMake layout has changed")
    replacement = '\n'.join([
        f'add_library(downward MODULE "{HERE / "bridge.cc"}")',
        f'target_include_directories(downward PRIVATE "{sysconfig.get_path("include")}" "${{CMAKE_CURRENT_SOURCE_DIR}}")',
        'set_target_properties(downward PROPERTIES PREFIX "" OUTPUT_NAME "_downward_native")',
    ])
    text = text.replace(original, replacement)
    text = text.replace('COMMAND git log', f'COMMAND git -c "safe.directory={source}" -C "{source}" log')
    text = text.replace('COMMAND git diff-index', f'COMMAND git -c "safe.directory={source}" -C "{source}" diff-index')
    cmake.write_text(text)
    build = directory / "build"
    subprocess.run(["cmake", "-S", str(overlay), "-B", str(build),
                    "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_CXX_COMPILER={args.compiler}",
                    "-DDISABLE_LIBRARIES_BY_DEFAULT=TRUE", "-DLIBRARY_MAX_HEURISTIC_ENABLED=TRUE",
                    "-DLIBRARY_LANDMARK_CUT_HEURISTIC_ENABLED=TRUE"], check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", str(args.jobs)], check=True)
    metadata = {**pin, "python": sys.version, "python_abi": sys.implementation.cache_tag,
                "build_type": "Release", "compiler": subprocess.check_output(
                    [args.compiler, "--version"], text=True).splitlines()[0],
                "binding_hashes": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                   for name in ("bridge.cc", "build.py", "upstream.json")},
                "module_sha256": hashlib.sha256((build / "search/_downward_native.so").read_bytes()).hexdigest()}
    (directory / "build-provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(build / "search/_downward_native.so")


if __name__ == "__main__":
    main()
