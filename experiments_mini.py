from planning_experiments.data_structures import *
from planning_experiments.launch_experiments import Executor
from os import path
import pkg_resources

PDDL_PATH = pkg_resources.resource_filename(__name__, 'benchmarks/')
MY_PLANNER_PATH = pkg_resources.resource_filename(__name__, 'planner')


class MyPlannerWrapper(Planner):

    def __init__(
            self,
            name: str,
            planner_path: str,
            metric: str,
            cp_heuristic: str,
            best_heuristic: str,
            worst_heuristic: str,
            size_heuristic: str,
            selector: str
            ) -> None:
        
        super().__init__(name, planner_path)
        self.metric = metric
        self.cp_heuristic = cp_heuristic
        self.best_heuristic = best_heuristic
        self.worst_heuristic = worst_heuristic
        self.size_heuristic = size_heuristic
        self.selector = selector

    def get_cmd(self, domain_path, instance_path, solution_path):
        return f'python {self.planner_path}/planner.py {domain_path} {instance_path} {solution_path} -m {self.metric} -ch {self.cp_heuristic} -bh {self.best_heuristic} -wh {self.worst_heuristic} -sh {self.size_heuristic} -s {self.selector}'
    

def main():

    results_folder = pkg_resources.resource_filename(__name__, 'MINI')
    env = Environment(results_folder, name='EVALUATION')
    
    timeout = 600
    configs = [
        ("bw", "hmax", "MinSum", "MaxSum", "Delta", "largestg",timeout),
    ]
    
    frozenlake = Domain('frozenlake', path.join(PDDL_PATH, 'frozenlake'))

    all_domains = [
        frozenlake,
    ]

    for config in configs:
        planner_name = "_".join(map(str,list(config)))

        my_planner = MyPlannerWrapper(planner_name, MY_PLANNER_PATH, metric=config[0], cp_heuristic=config[1], best_heuristic=config[2], worst_heuristic=config[3], size_heuristic=config[4], selector=config[5])

        env.add_run(system=my_planner, domains=all_domains)
    env.set_time(config[6])
    env.set_parallel_processes(2)
    executor = Executor(env)
    executor.run_experiments()

if __name__ == "__main__":
    main()
