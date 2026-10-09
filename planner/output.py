"""Historical policy text and eight-column statistics formats."""


def write_solution(policy, sol_number, pname, solution_folder, task=None):

    policy_str = ""
    for state, action in policy.strategy.items():
        facts = task.state_facts(state) if hasattr(task, "state_facts") else state
        policy_str += "If holds: " + "/".join(facts) + "\n"
        policy_str += "Execute: %s\n" % action[0]
        policy_str += "\n"

    with open("{}/{}.boand.{}.out".format(solution_folder, pname, str(sol_number).zfill(3)), "w") as out:
        out.write(policy_str)


def write_stats(stats, pname, solution_folder):

    stats_str = ""
    for i in range(len(stats["best"])):
        # Pyperplan LM-cut returns integral floats for this unit-cost planner.
        # Preserve the integer cost format expected by campaign result readers.
        best, worst = stats["best"][i], stats["worst"][i]
        best = int(best) if isinstance(best, float) and best.is_integer() else best
        worst = int(worst) if isinstance(worst, float) and worst.is_integer() else worst
        stats_str += ";".join(map(str,[best, worst, stats["size"][i], stats["time"][i], stats["iterations"][i], stats["expansions"][i], stats["generations"][i], stats["max_open"][i]])) + "\n"

    with open("{}/{}.stats".format(solution_folder, pname), "w") as out:
        out.write(stats_str)
