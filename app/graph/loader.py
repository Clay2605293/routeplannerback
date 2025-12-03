# app/graph/loader.py
import osmnx as ox
from typing import Tuple
from app.config import OSM_ADDRESS, OSM_DIST_METERS, OSM_NETWORK_TYPE

G = None       # grafo en lat/lon
G_proj = None  # grafo proyectado (para KD-tree, etc)


def load_graph() -> Tuple[object, object]:
    """
    Carga el grafo de OSM una sola vez, le agrega velocidades y tiempos de viaje,
    y regresa tanto el grafo original (lat/lon) como el proyectado.
    """
    global G, G_proj

    if G is not None and G_proj is not None:
        return G, G_proj

    # 1. Descargar grafo (lat/lon)
    G = ox.graph_from_address(
        OSM_ADDRESS,
        dist=OSM_DIST_METERS,
        network_type=OSM_NETWORK_TYPE,
    )

    # 2. Agregar velocidades y tiempos: en las versiones nuevas es ox.routing.*
    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)

    # 3. Proyectar el grafo para usar coordenadas planas (KD-tree, Voronoi, etc.)
    G_proj = ox.project_graph(G)

    return G, G_proj
