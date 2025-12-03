# app/algorithms/routing.py
from typing import List, Tuple
from simpleai.search import breadth_first, depth_first, uniform_cost, iterative_deepening, astar
from simpleai.search import SearchProblem
from app.graph.loader import load_graph


class GraphRouteProblem(SearchProblem):
    def __init__(self, origin_node: int, destination_node: int, cost_metric: str = "time"):
        self.G, self.G_proj = load_graph()
        self.cost_metric = cost_metric
        super().__init__(initial_state=origin_node)

        self.goal_state = destination_node

    def actions(self, state: int):
        return list(self.G_proj.successors(state))

    def result(self, state: int, action: int):
        return action

    def is_goal(self, state: int):
        return state == self.goal_state

    def cost(self, state1: int, action: int, state2: int):
        data = self.G_proj.edges[state1, state2, 0]
        if self.cost_metric == "time":
            return float(data.get("travel_time", 1.0))
        else:
            return float(data.get("length", 1.0))

    def heuristic(self, state: int):
        # heurística simple: distancia euclídea entre nodos
        import geopy.distance

        lat1 = self.G.nodes[state]["y"]
        lon1 = self.G.nodes[state]["x"]
        lat2 = self.G.nodes[self.goal_state]["y"]
        lon2 = self.G.nodes[self.goal_state]["x"]

        return geopy.distance.distance((lat1, lon1), (lat2, lon2)).meters


def run_search(origin_node: int, destination_node: int, algorithm: str, cost_metric: str):
    problem = GraphRouteProblem(origin_node, destination_node, cost_metric)

    if algorithm == "bfs":
        result = breadth_first(problem)
    elif algorithm == "dfs":
        result = depth_first(problem)
    elif algorithm == "ucs":
        result = uniform_cost(problem)
    elif algorithm == "iddfs":
        result = iterative_deepening(problem)
    elif algorithm == "astar":
        result = astar(problem)
    else:
        raise ValueError(f"Unknown algorithm {algorithm}")

    path_nodes = [state for state in result.path()[1:]]  # saltar el primer (None, initial)
    return result, path_nodes
