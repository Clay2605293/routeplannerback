# app/services/repository.py

from typing import Dict, List, Tuple, Optional

import math

from app.graph.loader import load_graph
from app.graph.kdtree import nearest_node_kd
from app.services.models import ServicePoint, ServiceType
from app.services.source_api import fetch_services_from_external_api


# Cache en memoria
_services_cache: Optional[List[ServicePoint]] = None
_node_to_service_cache: Optional[Dict[int, str]] = None  # node_id -> service_id
_service_by_id_cache: Dict[str, ServicePoint] = {}


def _ensure_services_loaded() -> List[ServicePoint]:
    """
    Carga los servicios desde la API externa (una sola vez) y les asigna nodo y coords (x,y).
    """
    global _services_cache, _service_by_id_cache

    if _services_cache is not None:
        return _services_cache

    services = fetch_services_from_external_api()
    _, G_proj = load_graph()
    proj_nodes = dict(G_proj.nodes(data=True))

    enriched: List[ServicePoint] = []

    for svc in services:
        # Mapear servicio a nodo de grafo más cercano
        node_id, _ = nearest_node_kd(svc.lat, svc.lon)
        node_data = proj_nodes.get(node_id)

        if node_data is None:
            # Si por alguna razón no hay datos proyectados, lo ignoramos
            continue

        svc.node_id = node_id
        svc.x = float(node_data["x"])
        svc.y = float(node_data["y"])

        enriched.append(svc)

    _services_cache = enriched
    _service_by_id_cache = {s.id: s for s in enriched}
    return _services_cache


def get_all_services() -> List[ServicePoint]:
    """
    Devuelve todos los servicios enriquecidos (con node_id, x, y).
    """
    return list(_ensure_services_loaded())


def _euclidean_xy(ax: float, ay: float, bx: float, by: float) -> float:
    dx = ax - bx
    dy = ay - by
    return math.sqrt(dx * dx + dy * dy)


def _build_node_to_service_partition() -> Dict[int, str]:
    """
    Construye una partición tipo Voronoi discreta:
      - Para cada nodo de G_proj, determina qué servicio (por distancia euclidiana en x,y)
        es el más cercano.
      - Regresa un dict: node_id -> service_id.

    Esto se hace una sola vez y se cachea en memoria.
    """
    global _node_to_service_cache

    if _node_to_service_cache is not None:
        return _node_to_service_cache

    services = _ensure_services_loaded()
    _, G_proj = load_graph()

    # Lista de servicios con coords
    svc_list: List[Tuple[str, float, float]] = [
        (s.id, s.x, s.y)
        for s in services
        if s.x is not None and s.y is not None
    ]

    node_to_service: Dict[int, str] = {}

    for node_id, data in G_proj.nodes(data=True):
        x = data["x"]
        y = data["y"]

        best_svc_id = None
        best_dist = float("inf")

        for svc_id, sx, sy in svc_list:
            d = _euclidean_xy(x, y, sx, sy)
            if d < best_dist:
                best_dist = d
                best_svc_id = svc_id

        if best_svc_id is not None:
            node_to_service[node_id] = best_svc_id

    _node_to_service_cache = node_to_service
    return _node_to_service_cache


def get_service_by_id(service_id: str) -> Optional[ServicePoint]:
    _ensure_services_loaded()
    return _service_by_id_cache.get(service_id)


def get_service_for_node(node_id: int) -> Optional[ServicePoint]:
    """
    Devuelve el servicio "propietario" del nodo según la partición Voronoi discreta.
    """
    partition = _build_node_to_service_partition()
    svc_id = partition.get(node_id)
    if svc_id is None:
        return None
    return get_service_by_id(svc_id)


def find_nearest_service_to_position(
    lat: float,
    lon: float,
    preferred_type: Optional[ServiceType] = None,
) -> Optional[ServicePoint]:
    """
    Encuentra el servicio más cercano a una posición arbitraria:
      1) Mapeamos la posición a node_id con el KD-tree del grafo.
      2) Usamos la partición discreta para saber qué servicio le corresponde.
      3) Opcionalmente, filtramos por tipo (preferred_type). Si el tipo no coincide,
         hacemos un fallback al 'servicio más cercano de ese tipo' por distancia.

    Esto respeta la idea de Voronoi: cada nodo del grafo pertenece a un servicio.
    """
    # Paso 1: punto -> nodo
    node_id, _ = nearest_node_kd(lat, lon)

    # Paso 2: Voronoi discreto
    svc = get_service_for_node(node_id)
    if svc is not None and (preferred_type is None or svc.type == preferred_type):
        return svc

    # Paso 3: fallback por tipo, si se pidió preferred_type
    services = get_all_services()
    filtered = [
        s for s in services
        if preferred_type is None or s.type == preferred_type
    ]
    if not filtered:
        return None

    # Buscamos el que tenga menor distancia en el plano lat/lon
    best_svc = None
    best_dist = float("inf")

    for s in filtered:
        d = _euclidean_xy(lat, lon, s.lat, s.lon)
        if d < best_dist:
            best_dist = d
            best_svc = s

    return best_svc
