# BOAND*
BOAND* is a novel heuristic search algorithm for Bi-Objective FOND Planning problems that computes Pareto-optimal solutions by navigating the space of possible policies. BOAND* is a generalization of the AND* algorithm (https://zenodo.org/records/7738316) to the bi-objective case.

To know more about BOAND*, please read our paper: Aineto and Scala, *"Cost-Optimal FOND Planning as Bi-Objective Best-First Search"*, ICAPS 2025.

**Disclaimer**: The current code of BOAND* was rushly implemented with little attention to performance. In the near future, we plan to revisit this line of research and develop a more polished implementation.

## Installation
This implementation of BOAND* is built on top publicly available planning libraries.

Installation instructions:

    - Install "pddl" library (source: https://github.com/AI-Planning/pddl/tree/v0.4.0) by running "pip install ." from the "planner/pddl/" folder 
    - Install "pyperplan" (source: https://github.com/aibasel/pyperplan/tree/main) by running "pip install ." from the "planner/pyperplan/" folder
    - Install the "Unified Planning Library" (source: https://github.com/aiplan4eu/unified-planning) by running "pip install unified-planning"
    - (Optinally) if you are missing some secondary libraries: "pip install -r requirements.txt" from root folder

## Running the Planner

Planner call:

    python planner/planner.py <domain_path> <problem_path> <solution_path> -m <metric> -ch <classical planning heuristic> -bh <best case heuristic> -wh <worst case heuristic>

Options:

    -m: for the metric(s). To choose among bw (best-worst), wb (worst-best), b (best) and w (worst). Choosing b or w executes the single-objective AND*.
    -ch: for the classical planning heuristic. To choose among hmax and lmcut.
    -bh: for the best case heuristic. To choose among BestBlind, SumMin and MinSum
    -wh: for the worst case heuristic. To choose among WorstBlind and MaxSum

Example:

    python planner/planner.py benchmarks/frozenlake/domain.pddl benchmarks/frozenlake/motivating.pddl . -m bw -ch hmax -bh MinSum -wh MaxSum

## Other contents

    - The "benchmarks" folder contains all domains and instances used in our experimental evaluation
    - The "results" folder contain all the solutions computed by the different configurations.
    - Results Analysis contains all the code used to generate our figures.
    - "FrozenLake Problem Generator" is, surprisingly, a problem generator for the FrozenLake domain.
