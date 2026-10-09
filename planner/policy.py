
CYCLE_COST = 999999

class Policy:
  __slots__ = ("strategy", "pending", "goal_states", "best_costs",
               "worst_costs", "closed", "cyclic", "proper")

  def __init__(self, strategy, pending, goal_states):
    self.strategy = strategy  # tile-action map
    
    # Pending are tiles reached that have not been mapped to an action yet
    self.pending = pending # tiles pending and their g values
    self.goal_states = goal_states
    
    self.best_costs = dict()
    self.worst_costs = dict()

    self.closed = False
    self.cyclic = False
    self.proper = False

  def copy(self, *, copy_bounds=True):
    new_policy = Policy(dict(),set(),set())
    new_policy.strategy = self.strategy.copy()
    new_policy.pending = self.pending.copy()
    new_policy.goal_states = self.goal_states.copy()
    if copy_bounds:
      new_policy.best_costs = self.best_costs.copy()
      new_policy.worst_costs = self.worst_costs.copy()
    new_policy.closed = self.closed
    new_policy.cyclic = self.cyclic
    new_policy.proper = self.proper

    return new_policy

  def __lt__(self, other):
    # if self.best_f < other.best_f:
    #   return True
    # elif self.best_f == other.best_f:
    #   return self.worst_f < other.worst_f
    # else:
    #     return False
    return True
    
  def __eq__(self, other):
    if isinstance(other, Policy):
        return self.strategy == other.strategy
    return False
  
  def get_best_g(self, state):
      return -1 if state == "dummy" else self.best_costs[state]

  def get_worst_g(self, state):
      return -1 if state == "dummy" else self.worst_costs.get(state, CYCLE_COST)

  def is_proper(self, task):
    if self.proper:
        return True
    # A closed reachable policy is proper exactly when all its states can
    # reach a goal. Build reverse edges once rather than enumerating paths.
    outcomes = getattr(task, "policy_outcomes", None)
    reached = {task.initial_state}
    frontier = [task.initial_state]
    predecessors = {}
    goals = []
    for state in frontier:
        if task.goal_reached(state):
            goals.append(state)
            continue
        action = self.strategy.get(state)
        if action is None:
            return False
        children = outcomes(state, action[0]) if outcomes is not None else {op.apply(state) for op in action[1]}
        for child in children:
            predecessors.setdefault(child, []).append(state)
            if child not in reached:
                reached.add(child)
                frontier.append(child)
    good = set(goals)
    for state in goals:
        for parent in predecessors.get(state, ()):
            if parent not in good:
                good.add(parent)
                goals.append(parent)
    self.proper = reached <= good
    return self.proper

  def is_closed(self):
    if not self.closed:
        self.closed = len(self.pending) == 0
    return self.closed
