"""Historical command-line handling and defaults."""
from .search import boand_star


def main(argv, arc):
    # print(argv, arc)

    # print("Example call: python planner <domain> <problem> -m <metric> -tb <0/1> -h <heuristic> -s <selector>")

    domain_file = argv[1]
    problem_file = argv[2]
    solution_folder = argv[3]

    metric = "bw"
    if "-m" in argv:
        index = argv.index("-m")
        metric = argv[index+1]
    heuristic = "hmax"
    if "-ch" in argv:
        index = argv.index("-ch")
        heuristic = argv[index+1]
    best_heuristic = "MinSum"
    if "-bh" in argv:
        index = argv.index("-bh")
        best_heuristic = argv[index+1]
    worst_heuristic = "MaxSum"
    if "-wh" in argv:
        index = argv.index("-wh")
        worst_heuristic = argv[index+1]
    size_heuristic = "Delta"
    if "-sh" in argv:
        index = argv.index("-sh")
        size_heuristic = argv[index+1]
    selector = "bounds"
    if "-s" in argv:
        index = argv.index("-s")
        selector = argv[index+1]
    backend = "pyperplan"
    if "--backend" in argv:
        backend = argv[argv.index("--backend")+1]

    boand_star(domain_file, problem_file, solution_folder, use_metric=metric, use_cp_heuristic=heuristic, use_best_case_heuristic=best_heuristic, use_worst_case_heuristic=worst_heuristic, use_size_heuristic=size_heuristic, use_selector=selector, backend=backend)


def test():
    # PARSING ERRORS:
    # blocksworld(s) - NNF (not (= ?b1 ?b2))
    # faults(s) - same name "fault" for object and predicate
    # puffbot_dialogue_pddl - same name "initiate" for action and predicate
    # st_faults - same name "fault"
    # st_mapfdu - determinizer error
    # tidyup-mdp - NNF (not (= a b))
    # zenotravel - forall


    domain = "frozenlake"

    domain_file = "fond-domains/benchmarks/{}/domain.pddl".format(domain)
    problem_file = "fond-domains/benchmarks/{}/p_1_3.pddl".format(domain)

    domain_file = "benchmarks/{}/domain.pddl".format(domain)
    problem_file = "benchmarks/{}/motivating.pddl".format(domain)

    solution = boand_star(domain_file, problem_file, problem_file[:problem_file.rfind("/")], use_metric="bw", use_cp_heuristic="hmax", use_best_case_heuristic="MinSum", use_worst_case_heuristic="MaxSum", use_size_heuristic="Zero", use_selector="random")
