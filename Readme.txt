This implementation of BOAND* is built on top publicly available planning libraries.

Installation instructions:
    - Install pddl library from the "planner/pddl/" folder (source: https://github.com/AI-Planning/pddl/tree/v0.4.0)
    - Install pyperplan from the "planner/pyperplan/" folder (source: https://github.com/aibasel/pyperplan/tree/main)
    - Install the Unified Planning Library (source: https://github.com/aiplan4eu/unified-planning)
    - Other libraries: "pip install -r requirements.txt" from root folder

Planner call:

    python planner/planner.py <domain_path> <problem_path> <solution_path> -m <metric> -ch <classical planning heuristic> -bh <best case heuristic> -wh <worst case heuristic>

Options:

    -m: for the metric(s). To choose among bw (best-worst), wb (worst-best), b (best) and w (worst). Choosing b or w executes the single-objective AND*.
    -ch: for the classical planning heuristic. To choose among hmax and lmcut.
    -bh: for the best case heuristic. To choose among BestBlind, SumMin and MinSum
    -wh: for the worst case heuristic. To choose among WorstBlind and MaxSum

Example:

    python planner/planner.py benchmarks/frozenlake/domain.pddl benchmarks/frozenlake/motivating.pddl . -m bw -ch hmax -bh MinSum -wh MaxSum


Other contents:
    - The "benchmarks" folder contains all domains and instances used in our experimental evaluation
    - The "results" folder contain all the solutions computed by the different configurations.
    - Results Analysis contains all the code used to generate our figures.
    - "FrozenLake Problem Generator" is, surprisingly, a problem generator for the FrozenLake domain.
