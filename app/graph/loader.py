# app/graph/loader.py
from typing import Tuple
import osmnx as ox
from app.config import OSM_ADDRESS, OSM_DIST_METERS, OSM_NETWORK_TYPE

G = None       # grafo en lat/lon
G_proj = None  # grafo proyectado


def load_graph() -> Tuple[object, object]:
    global G, G_proj
    if G is not None and G_proj is not None:
        return G, G_proj

    G = ox.graph_from_address(
        OSM_ADDRESS,
        dist=OSM_DIST_METERS,
        network_type=OSM_NETWORK_TYPE,
    )
    G_proj = ox.project_graph(G)

    # Opcional: agregar speeds y travel_time aquí
    G_proj = ox.speed.add_edge_speeds(G_proj)
    G_proj = ox.speed.add_edge_travel_times(G_proj)

    return G, G_proj
