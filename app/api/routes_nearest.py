# app/api/routes_nearest.py
from fastapi import APIRouter
from typing import List, Dict
import time

from app.models import (
    NearestNodeRequest,
    NearestNodeResult,
    NearestNodeBatchRequest,
    NearestNodeBatchResultItem,
    NearestNodeBatchResponse,
    LatLon,
)

router = APIRouter()


@router.post("/nearest-node", response_model=NearestNodeResult)
def nearest_node(req: NearestNodeRequest):
    """
    Versión dummy: regresa el mismo punto como nodo.
    Después conectamos con KD-tree y búsqueda exhaustiva.
    """
    t0 = time.perf_counter()

    # TODO: aquí llamarás a nearest_node_kd o brute force de tu módulo kdtree
    dummy_node_id = 1
    dummy_node_lat = req.lat
    dummy_node_lon = req.lon
    dummy_distance_m = 0.0

    dt_ms = (time.perf_counter() - t0) * 1000.0

    return NearestNodeResult(
        lat=req.lat,
        lon=req.lon,
        method=req.method,
        node_id=dummy_node_id,
        node_lat=dummy_node_lat,
        node_lon=dummy_node_lon,
        distance_m=dummy_distance_m,
        time_ms=dt_ms,
    )


@router.post("/nearest-node/batch", response_model=NearestNodeBatchResponse)
def nearest_node_batch(req: NearestNodeBatchRequest):
    """
    Versión dummy: calcula nearest-node para cada punto con los métodos indicados.
    Ahora mismo solo simula tiempos; luego se sustituye por KD-tree y brute force reales.
    """
    results: List[NearestNodeBatchResultItem] = []
    summary: Dict[str, Dict[str, float]] = {}

    # Inicializar acumuladores
    for method in req.methods:
        summary[method] = {
            "total_time_ms": 0.0,
            "max_time_ms": 0.0,
            "count": 0.0,
        }

    for idx, point in enumerate(req.points):
        by_method: Dict[str, NearestNodeResult] = {}

        for method in req.methods:
            t0 = time.perf_counter()

            # TODO: aquí va KD-tree vs brute force real
            dummy_node_id = 1
            dummy_node_lat = point.lat
            dummy_node_lon = point.lon
            dummy_distance_m = 0.0

            dt_ms = (time.perf_counter() - t0) * 1000.0

            res = NearestNodeResult(
                lat=point.lat,
                lon=point.lon,
                method=method,
                node_id=dummy_node_id,
                node_lat=dummy_node_lat,
                node_lon=dummy_node_lon,
                distance_m=dummy_distance_m,
                time_ms=dt_ms,
            )
            by_method[method] = res

            summary[method]["total_time_ms"] += dt_ms
            summary[method]["max_time_ms"] = max(summary[method]["max_time_ms"], dt_ms)
            summary[method]["count"] += 1.0

        results.append(
            NearestNodeBatchResultItem(
                index=idx,
                lat=point.lat,
                lon=point.lon,
                by_method=by_method,
            )
        )

    # Calcular promedios finales
    summary_out: Dict[str, Dict[str, float]] = {}
    for method, stats in summary.items():
        count = max(stats["count"], 1.0)
        summary_out[method] = {
            "avg_time_ms": stats["total_time_ms"] / count,
            "max_time_ms": stats["max_time_ms"],
        }

    return NearestNodeBatchResponse(results=results, summary=summary_out)
