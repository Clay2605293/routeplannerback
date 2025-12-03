# app/api/routes_routing.py
from fastapi import APIRouter
from app.models import RouteRequest, RouteResponse, LatLon, RouteStats

router = APIRouter()


@router.post("/route", response_model=RouteResponse)
def compute_route(req: RouteRequest):
    """
    Endpoint de prueba: por ahora regresa una ruta dummy recta
    entre origen y destino, solo para que el backend levante.
    Luego lo sustituimos con SimpleAI + OSMnx.
    """
    # Ruta dummy: solo conectamos origen y destino como dos puntos
    path_nodes = [1, 2]

    geometry = [
        LatLon(lat=req.origin.lat, lon=req.origin.lon),
        LatLon(lat=req.destination.lat, lon=req.destination.lon),
    ]

    distance_m = 1000.0
    travel_time_s = 120.0

    stats = RouteStats(
        algorithm=req.algorithm,
        cost_metric=req.cost_metric,
        expanded_nodes=2,
        time_ms=0.1,
    )

    return RouteResponse(
        origin=req.origin,
        destination=req.destination,
        origin_node=path_nodes[0],
        destination_node=path_nodes[-1],
        path_nodes=path_nodes,
        geometry=geometry,
        distance_m=distance_m,
        travel_time_s=travel_time_s,
        stats=stats,
    )
