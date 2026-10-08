
CYCLE_COST = 999999

class Policy:
  def __init__(self, strategy, pending, goal_states):
    self.strategy = strategy  # tile-action map
    
    # Pending are tiles reached that have not been mapped to an action yet
    self.pending = pending # tiles pending and their g values
    self.goal_states = goal_states
    
    self.best_ancestors = dict()
    self.worst_ancestors = dict()

    self.closed = False
    self.cyclic = False
    self.proper = False

  def copy(self):
    new_policy = Policy(dict(),set(),set())
    new_policy.strategy = self.strategy.copy()
    new_policy.pending = self.pending.copy()
    new_policy.goal_states = self.goal_states.copy()
    new_policy.best_ancestors = self.best_ancestors.copy()
    new_policy.worst_ancestors = self.worst_ancestors.copy()
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
      current = state
      g = 0
      while current != "dummy":
          current = self.best_ancestors.get(current,None)
          g+=1
      return g-1

  def get_worst_g(self,state):
      ancestors = set()
      ancestors.add(state)
      
      current = state
      g = 0
      while current != "dummy": # reaches the initial state
          current = self.worst_ancestors.get(current,None)
          if current in ancestors:
              return CYCLE_COST
          g+=1
          ancestors.add(current)
      return g-1
    
  
  def is_proper(self, task):
    if not self.proper:
        goal_trajectories = list()
        frontier = {task.initial_state:[]}
        cycle_roots = set()
        while frontier:
            state,ancestors = frontier.popitem()
            action = self.strategy.get(state, None)
            if action is None:
                return False
            else:
                reached_states = {det_action.apply(state) for det_action in action[1]}
                for reached_state in reached_states:
                    if reached_state in ancestors:
                        cycle_roots.add(reached_state)
                    elif task.goal_reached(reached_state):
                        goal_trajectories.append(ancestors)
                    else:
                        new_ancestors = ancestors.copy()
                        new_ancestors.append(state)
                        frontier[reached_state] = new_ancestors
        # Every cycle root must be goal reaching
        for root in cycle_roots:
            goal_reaching = False
            for trajectory in goal_trajectories:
                if root in trajectory:
                    goal_reaching = True
                    break
            if not goal_reaching:
                return False
        
        self.proper = True
    return self.proper

  def is_closed(self):
    if not self.closed:
        self.closed = len(self.pending) == 0
    return self.closed