"""Task-local hmax implementation with one cost calculation per operator."""
import heapq
from pyperplan.heuristics.relaxation import hMaxHeuristic


class OperatorCostHMaxHeuristic(hMaxHeuristic):
    def __init__(self, task):
        super().__init__(task)
        for operator in self.operators:
            # These relaxed operators are owned by this heuristic instance.
            operator.effect_facts = tuple(self.facts[effect] for effect in operator.add_effects)

    def dijkstra(self, queue):
        achieved_goals = set()
        while not self.finished(achieved_goals, queue):
            distance, _, fact = heapq.heappop(queue)
            if fact.name in self.goals:
                achieved_goals.add(fact.name)
            if fact.expanded:
                continue
            for operator in fact.precondition_of:
                operator.counter -= 1
                if operator.counter <= 0:
                    # Preconditions settle in nondecreasing distance order.
                    # The last settled precondition supplies their maximum;
                    # the synthetic start entry has distance zero for empty ones.
                    operator_distance = distance + operator.cost
                    for neighbor in operator.effect_facts:
                        if operator_distance < neighbor.distance:
                            neighbor.distance = operator_distance
                            neighbor.sa_set = None
                            neighbor.cheapest_achiever = operator
                            heapq.heappush(queue, (operator_distance, self.tie_breaker, neighbor))
                            self.tie_breaker += 1
            fact.expanded = True
