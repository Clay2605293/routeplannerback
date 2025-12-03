# app/api/routes_routing.py
from fastapi import APIRouter
from typing import List
import time

from app.models import (
    RouteRequest,
    RouteResponse,
    RouteStats,
    RouteCompareRequest,
    RouteCompareResponse,
    RouteCompareResult,
    LatLon,
    DemoTrip,
)

router = APIRouter()


@router.post("/route", response_model=RouteResponse)
def compute_route(req: RouteRequest):
    """
    Versión dummy de /api/route.
    Luego se reemplaza por llamada a SimpleAI (BFS/DFS/UCS/IDDFS/A*).
    """
    t0 = time.perf_counter()

    # TODO: llamar a run_search(origin_node, destination_node, req.algorithm, req.cost_metric)
    origin_node = 1
    destination_node = 2
    path_nodes = [origin_node, destination_node]

    geometry = [
        LatLon(lat=req.origin.lat, lon=req.origin.lon),
        LatLon(lat=req.destination.lat, lon=req.destination.lon),
    ]

    distance_m = 1000.0
    travel_time_s = 120.0

    dt_ms = (time.perf_counter() - t0) * 1000.0

    stats = RouteStats(
        algorithm=req.algorithm,
        cost_metric=req.cost_metric,
        expanded_nodes=len(path_nodes),
        time_ms=dt_ms,
    )

    return RouteResponse(
        origin=req.origin,
        destination=req.destination,
        origin_node=origin_node,
        destination_node=destination_node,
        path_nodes=path_nodes,
        geometry=geometry,
        distance_m=distance_m,
        travel_time_s=travel_time_s,
        stats=stats,
    )


@router.post("/route/compare", response_model=RouteCompareResponse)
def compare_routes(req: RouteCompareRequest):
    """
    Versión dummy de /api/route/compare.
    Para cada algoritmo, simula una ruta y tiempos distintos.
    Luego se conectará a SimpleAI.
    """
    origin_node = 1
    destination_node = 2

    results: List[RouteCompareResult] = []
    base_distance = 3200.0
    base_time_s = 620.0

    for alg in req.algorithms:
        t0 = time.perf_counter()

        # TODO: llamar a run_search y capturar métricas reales
        # Por ahora simulamos:
        factor = {
            "bfs": 1.03,
            "dfs": 3.0,
            "ucs": 1.0,
            "iddfs": 1.5,
            "astar": 1.0,
        }.get(alg, 1.0)

        distance_m = base_distance * factor
        travel_time_s = base_time_s * factor
        expanded_nodes = int(1000 * factor)

        dt_ms = (time.perf_counter() - t0) * 1000.0

        results.append(
            RouteCompareResult(
                algorithm=alg,
                found=True,
                distance_m=distance_m,
                travel_time_s=travel_time_s,
                expanded_nodes=expanded_nodes,
                time_ms=dt_ms,
                is_default_choice=(alg == "astar"),
            )
        )

    return RouteCompareResponse(
        origin_node=origin_node,
        destination_node=destination_node,
        results=results,
    )


@router.get("/demo/trips", response_model=List[DemoTrip])
def get_demo_trips():
    """
    Devuelve una lista de viajes demo (Uber-like) para probar el front.
    Luego puedes ajustar coordenadas a tu ciudad concreta.
    """
    trips: List[DemoTrip] = [
        DemoTrip(
            id="trip_1",
            client_name="Cliente 1",
            pickup=LatLon(lat=20.6736, lon=-103.3440),
            destination=LatLon(lat=20.6800, lon=-103.3500),
        ),
        DemoTrip(
            id="trip_2",
            client_name="Cliente 2",
            pickup=LatLon(lat=20.6750, lon=-103.3420),
            destination=LatLon(lat=20.6850, lon=-103.3550),
        ),
    ]
    return trips
