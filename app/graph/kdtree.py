# app/graph/kdtree.py
from typing import Tuple, List
import time
from scipy.spatial import KDTree
from app.graph.loader import load_graph

_kd_tree = None
_kd_coords: List[Tuple[float, float]] = []
_kd_node_ids: List[int] = []
_kd_build_time_ms: float = 0.0


def build_kd_tree():
    global _kd_tree, _kd_coords, _kd_node_ids, _kd_build_time_ms

    _, G_proj = load_graph()
    nodes = list(G_proj.nodes(data=True))
    coords = [(d["x"], d["y"]) for (_, d) in nodes]
    node_ids = [node_id for (node_id, _) in nodes]

    t0 = time.perf_counter()
    _kd_tree = KDTree(coords)
    _kd_build_time_ms = (time.perf_counter() - t0) * 1000.0

    _kd_coords = coords
    _kd_node_ids = node_ids

    return _kd_build_time_ms


def get_kd_build_time_ms() -> float:
    if _kd_tree is None:
        build_kd_tree()
    return _kd_build_time_ms


def nearest_node_kd(lat: float, lon: float) -> Tuple[int, float]:
    G, G_proj = load_graph()
    if _kd_tree is None:
        build_kd_tree()

    # proyectar el punto a coordenadas del grafo proyectado
    point_geom = ox.projection.project_geometry(
        {"type": "Point", "coordinates": (lon, lat)}, to_crs=G_proj.graph["crs"]
    )[0]
    x, y = point_geom.x, point_geom.y

    dist, idx = _kd_tree.query((x, y))
    node_id = _kd_node_ids[idx]

    return node_id, float(dist)
