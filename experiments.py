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

    results_folder = pkg_resources.resource_filename(__name__, 'ICAPS')
    env = Environment(results_folder, name='EVALUATION')
    
    timeout = 600
    configs = [
        # ("b", "hadd", "Blind", "Blind", "Zero", "random",timeout),
        # ("b", "hadd", "SumMin", "Blind", "Zero", "random",timeout),
        # ("b", "hadd", "MinSum", "Blind", "Zero", "random",timeout),
        # ("w", "hadd", "Blind", "Blind", "Zero", "random",timeout),
        # ("w", "hadd", "Blind", "MaxSum", "Zero", "random",timeout),
        # ("bw", "hadd", "MinSum", "MaxSum", "Zero", "random",timeout),
        # ("bw", "hadd", "MinSum", "MaxSum", "Delta", "random",timeout),
        # ("bw", "hadd", "MinSum", "MaxSum", "Zero", "largestg",timeout),
        # ("bw", "hadd", "MinSum", "MaxSum", "Delta", "largestg",timeout),
        # ("bw", "hadd", "MinSum", "MaxSum", "Delta", "bounds",timeout),
        # ("wb", "hadd", "MinSum", "MaxSum", "Delta", "largestg",timeout),
        # ("bw", "hadd", "SumMin", "MaxSum", "Delta", "largestg",timeout),
        ("wb", "hadd", "SumMin", "MaxSum", "Delta", "largestg",timeout),
        ("b", "hadd", "MinSum", "Blind", "Delta", "random",timeout)

    ]
    
    icylake = Domain('icylake', path.join(PDDL_PATH, 'icylake'))

    beamwalk = Domain('bream-walk', path.join(PDDL_PATH, 'beam-walk'))
    blocksworld_ex = Domain('blocksworld-ex', path.join(PDDL_PATH, 'blocksworld-ex'))
    chain_of_rooms = Domain('chain-of-rooms', path.join(PDDL_PATH, 'chain-of-rooms'))
    doors = Domain('doors', path.join(PDDL_PATH, 'doors'))
    earth_observation = Domain('earth-observation', path.join(PDDL_PATH, 'earth-observation'))
    elevators = Domain('elevators', path.join(PDDL_PATH, 'elevators'))
    frozenlake = Domain('frozenlake', path.join(PDDL_PATH, 'frozenlake'))
    islands = Domain('islands', path.join(PDDL_PATH, 'islands'))
    mod_first_responders = Domain('mod_first_responders', path.join(PDDL_PATH, 'mod_first_responders'))
    st_blocksworld = Domain('st_blocksworld', path.join(PDDL_PATH, 'st_blocksworld'))
    st_first_responders = Domain('st_first_responders', path.join(PDDL_PATH, 'st_first_responders'))
    st_tires = Domain('st_tires', path.join(PDDL_PATH, 'st_tires'))
    tireworld = Domain('tireworld', path.join(PDDL_PATH, 'tireworld'))
    tireworld_truck = Domain('tireworld-truck', path.join(PDDL_PATH, 'tireworld-truck'))

    all_domains = [
        # icylake,
        beamwalk,
        blocksworld_ex,
        chain_of_rooms,
        doors,
        earth_observation,
        elevators,
        frozenlake,
        islands,
        mod_first_responders,
        # ## st_blocksworld,
        # ## st_first_responders,
        st_tires,
        tireworld,
        tireworld_truck
    ]

    for config in configs:
        planner_name = "_".join(map(str,list(config)))

        my_planner = MyPlannerWrapper(planner_name, MY_PLANNER_PATH, metric=config[0], cp_heuristic=config[1], best_heuristic=config[2], worst_heuristic=config[3], size_heuristic=config[4], selector=config[5])

        env.add_run(system=my_planner, domains=all_domains)
    env.set_time(config[6])
    env.set_parallel_processes(12)
    executor = Executor(env)
    executor.run_experiments()

if __name__ == "__main__":
    main()
