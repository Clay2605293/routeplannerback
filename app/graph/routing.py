# app/graph/routing.py

from time import perf_counter
from typing import List, Dict, Literal, Any

from simpleai.search import SearchProblem
from simpleai.search.traditional import (
    breadth_first,
    depth_first,
    uniform_cost,
    astar,
    iterative_limited_depth_first,
)

from app.graph.loader import load_graph


AlgorithmName = Literal["bfs", "dfs", "ucs", "iddfs", "astar"]
CostMetric = Literal["distance", "time"]


def _euclidean_xy(ax: float, ay: float, bx: float, by: float) -> float:
    dx = ax - bx
    dy = ay - by
    return (dx * dx + dy * dy) ** 0.5


def _get_edge_best(G_proj, u: int, v: int) -> Dict[str, Any]:
    """
    Regresa la mejor arista u->v (si hay varias paralelas) usando length como referencia.
    """
    data_uv = G_proj.get_edge_data(u, v)
    if not data_uv:
        raise ValueError(f"No edge data between {u} and {v}")

    # data_uv es un dict {key: attr_dict}
    best = min(data_uv.values(), key=lambda d: d.get("length", 0.0))
    return best


def compute_path_metrics(path_nodes: List[int]) -> Dict[str, float]:
    """
    Dado un camino como lista de nodos, calcula:
    - distance_m: suma de 'length' en las aristas
    - travel_time_s: suma de 'travel_time' (si existe). Si una arista no tiene travel_time,
                     se aproxima usando length / 13.9 (~50 km/h).
    Si el camino está vacío o tiene 1 nodo, regresa 0 en ambos.
    """
    if len(path_nodes) < 2:
        return {
            "distance_m": 0.0,
            "travel_time_s": 0.0,
        }

    _, G_proj = load_graph()

    total_dist = 0.0
    total_time = 0.0

    for u, v in zip(path_nodes, path_nodes[1:]):
        edge = _get_edge_best(G_proj, u, v)
        length = float(edge.get("length", 0.0))
        travel_time = edge.get("travel_time")

        total_dist += length
        if travel_time is not None:
            total_time += float(travel_time)
        else:
            # velocidad aprox 50 km/h
            total_time += length / 13.9

    return {
        "distance_m": total_dist,
        "travel_time_s": total_time,
    }


class RoutePlanningProblem(SearchProblem):
    """
    Problema de búsqueda sobre el grafo proyectado (G_proj).
    - Estado: node_id (int)
    - Acciones: node_ids vecinos alcanzables
    """

    def __init__(
        self,
        initial_state: int,
        goal_state: int,
        cost_metric: CostMetric = "distance",
    ):
        super().__init__(initial_state=initial_state)
        self.goal_state = goal_state
        self.cost_metric: CostMetric = cost_metric

        # Usamos el grafo proyectado para distancias en metros
        _, self.G_proj = load_graph()
        # Precache de coords proyectadas
        self._xy = {
            n: (data["x"], data["y"])
            for n, data in self.G_proj.nodes(data=True)
        }

    # Métodos que SimpleAI espera en SearchProblem

    def actions(self, state: int) -> List[int]:
        """Vecinos sucesores del nodo actual."""
        return list(self.G_proj.successors(state))

    def result(self, state: int, action: int) -> int:
        """El resultado de aplicar la acción es simplemente ir al vecino."""
        return action

    def is_goal(self, state: int) -> bool:
        return state == self.goal_state

    def cost(self, state: int, action: int, state2: int) -> float:
        """
        Costo de paso entre state1 y state2.
        - distance: length en metros
        - time: travel_time en segundos (o approx si no existe)
        """
        edge = _get_edge_best(self.G_proj, state, state2)
        if self.cost_metric == "time":
            tt = edge.get("travel_time")
            if tt is not None:
                return float(tt)
            # fallback si no hubiera travel_time
            length = float(edge.get("length", 0.0))
            return length / 13.9  # aprox
        else:
            # distance
            return float(edge.get("length", 0.0))

    def heuristic(self, state: int) -> float:
        """
        Heurística para A*:
        - Para distance: distancia euclidiana en metros.
        - Para time: distancia / velocidad_promedio aprox.
        """
        x1, y1 = self._xy[state]
        x2, y2 = self._xy[self.goal_state]
        dist = _euclidean_xy(x1, y1, x2, y2)

        if self.cost_metric == "time":
            return dist / 13.9  # ~50 km/h
        else:
            return dist


def run_search(
    origin_node: int,
    goal_node: int,
    algorithm: AlgorithmName,
    cost_metric: CostMetric = "distance",
) -> Dict[str, Any]:
    """
    Ejecuta uno de los algoritmos de SimpleAI sobre el grafo.

    origin_node y goal_node son ids de nodos de G_proj.
    """
    problem = RoutePlanningProblem(
        initial_state=origin_node,
        goal_state=goal_node,
        cost_metric=cost_metric,
    )

    algo = algorithm.lower()
    kwargs = {"graph_search": True}

    if algo == "bfs":
        search_fn = breadth_first
    elif algo == "dfs":
        search_fn = depth_first
    elif algo == "ucs":
        search_fn = uniform_cost
    elif algo == "iddfs":
        search_fn = iterative_limited_depth_first
    elif algo == "astar":
        search_fn = astar
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    start = perf_counter()
    result_node = search_fn(problem, **kwargs)
    elapsed_ms = (perf_counter() - start) * 1000.0

    if result_node is None:
        return {
            "found": False,
            "time_ms": elapsed_ms,
            "path": [],
            "path_nodes": [],
            "expanded_nodes": None,
        }

    # result_node.path() -> lista de (action, state)
    steps = result_node.path()
    path_states = [state for (action, state) in steps]

    return {
        "found": True,
        "time_ms": elapsed_ms,
        "path": path_states,
        "path_nodes": path_states,  # alias para compute_path_metrics
        "expanded_nodes": None,
    }


