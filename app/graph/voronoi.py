# app/graph/voronoi.py
from typing import Any, List
from app.models import ServiceInfo

_voronoi_diagram: Any = None

def build_voronoi(services: List[ServiceInfo]) -> None:
    # Aquí harás la partición de Voronoi en coordenadas proyectadas
    global _voronoi_diagram
    _voronoi_diagram = None


def find_service_for_point(lat: float, lon: float, services: List[ServiceInfo]) -> ServiceInfo:
    # Usar el diagrama de Voronoi para decidir qué servicio es el más cercano
    # Por ahora, puedes regresar el primer servicio como dummy
    return services[0]
