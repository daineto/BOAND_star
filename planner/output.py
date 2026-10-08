"""Historical policy text and eight-column statistics formats."""


def write_solution(policy, sol_number, pname, solution_folder):

    policy_str = ""
    for state, action in policy.strategy.items():
        policy_str += "If holds: " + "/".join(state) + "\n"
        policy_str += "Execute: %s\n" % action[0]
        policy_str += "\n"

    with open("{}/{}.boand.{}.out".format(solution_folder, pname, str(sol_number).zfill(3)), "w") as out:
        out.write(policy_str)


def write_stats(stats, pname, solution_folder):

    stats_str = ""
    for i in range(len(stats["best"])):
        stats_str += ";".join(map(str,[stats["best"][i], stats["worst"][i], stats["size"][i], stats["time"][i], stats["iterations"][i], stats["expansions"][i], stats["generations"][i], stats["max_open"][i]])) + "\n"

    with open("{}/{}.stats".format(solution_folder, pname), "w") as out:
        out.write(stats_str)
