"""Task-local hmax implementation with one cost calculation per operator."""
import heapq
from pyperplan.heuristics.relaxation import hMaxHeuristic


class OperatorCostHMaxHeuristic(hMaxHeuristic):
    def dijkstra(self, queue):
        achieved_goals = set()
        while not self.finished(achieved_goals, queue):
            _, _, fact = heapq.heappop(queue)
            if fact.name in self.goals:
                achieved_goals.add(fact.name)
            if fact.expanded:
                continue
            for operator in fact.precondition_of:
                operator.counter -= 1
                if operator.counter <= 0:
                    # The operator's hmax cost is independent of its add effect.
                    # Preserve effect iteration and heap tie order.
                    _, distance = self.get_cost(operator, fact)
                    for effect in operator.add_effects:
                        neighbor = self.facts[effect]
                        if distance < neighbor.distance:
                            neighbor.distance = distance
                            neighbor.sa_set = None
                            neighbor.cheapest_achiever = operator
                            heapq.heappush(queue, (distance, self.tie_breaker, neighbor))
                            self.tie_breaker += 1
            fact.expanded = True
