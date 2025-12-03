# app/graph/kdtree.py
from typing import List, Tuple
import time

import osmnx as ox
from osmnx.projection import project_geometry
from shapely.geometry import Point
from scipy.spatial import KDTree
import geopy.distance

from app.graph.loader import load_graph



_kd_tree: KDTree | None = None
_kd_coords: List[Tuple[float, float]] = []
_kd_node_ids: List[int] = []
_kd_build_time_ms: float = 0.0


def build_kd_tree() -> float:
    """
    Construye el KD-tree sobre el grafo proyectado.
    Solo se ejecuta una vez; después reutiliza la estructura.
    Regresa el tiempo de construcción en milisegundos.
    """
    global _kd_tree, _kd_coords, _kd_node_ids, _kd_build_time_ms

    if _kd_tree is not None:
        return _kd_build_time_ms

    _, G_proj = load_graph()
    nodes = list(G_proj.nodes(data=True))

    coords: List[Tuple[float, float]] = []
    node_ids: List[int] = []

    for node_id, data in nodes:
        coords.append((data["x"], data["y"]))
        node_ids.append(node_id)

    t0 = time.perf_counter()
    kd = KDTree(coords)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    _kd_tree = kd
    _kd_coords = coords
    _kd_node_ids = node_ids
    _kd_build_time_ms = dt_ms

    return dt_ms


def get_kd_build_time_ms() -> float:
    """
    Regresa el tiempo que tomó construir el KD-tree.
    Si aún no existe, lo construye primero.
    """
    if _kd_tree is None:
        build_kd_tree()
    return _kd_build_time_ms


def _latlon_to_xy(lat: float, lon: float, G_proj) -> Tuple[float, float]:
    """
    Proyecta un punto (lat, lon) al sistema de coordenadas de G_proj.
    Usa osmnx.projection.project_geometry con un shapely Point.
    """
    point = Point(lon, lat)  # shapely Point (x=lon, y=lat)
    geom_proj, _ = project_geometry(
        point,
        to_crs=G_proj.graph["crs"],
    )
    return geom_proj.x, geom_proj.y




def nearest_node_kd(lat: float, lon: float) -> Tuple[int, float]:
    """
    Busca el nodo más cercano usando KD-tree.
    Regresa (node_id, distancia_en_unidades_del_crs).
    """
    from app.graph.loader import load_graph  # para evitar ciclos de import

    _, G_proj = load_graph()

    if _kd_tree is None:
        build_kd_tree()

    x, y = _latlon_to_xy(lat, lon, G_proj)
    dist, idx = _kd_tree.query((x, y))
    node_id = _kd_node_ids[idx]

    # dist está en unidades del sistema proyectado (usualmente metros)
    return node_id, float(dist)


def nearest_node_bruteforce(lat: float, lon: float) -> Tuple[int, float]:
    """
    Busca el nodo más cercano con una búsqueda exhaustiva (O(N)).
    Usa distancia geodésica (geopy) sobre G (lat/lon).
    Regresa (node_id, distancia_metros).
    """
    G, _ = load_graph()

    best_node = None
    best_dist = float("inf")

    for node_id, data in G.nodes(data=True):
        node_lat = data["y"]
        node_lon = data["x"]
        d = geopy.distance.distance((lat, lon), (node_lat, node_lon)).m
        if d < best_dist:
            best_dist = d
            best_node = node_id

    return best_node, best_dist
