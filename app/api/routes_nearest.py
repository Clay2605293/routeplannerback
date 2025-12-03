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
)
from app.graph.loader import load_graph
from app.graph.kdtree import nearest_node_kd, nearest_node_bruteforce

router = APIRouter()


@router.post("/nearest-node", response_model=NearestNodeResult)
def nearest_node(req: NearestNodeRequest):
    """
    Busca el nodo más cercano a un punto (lat, lon).
    method = "kd" usa KD-tree.
    method = "bruteforce" recorre todos los nodos.
    """
    G, _ = load_graph()

    t0 = time.perf_counter()

    if req.method == "kd":
        node_id, dist = nearest_node_kd(req.lat, req.lon)
    else:
        node_id, dist = nearest_node_bruteforce(req.lat, req.lon)

    dt_ms = (time.perf_counter() - t0) * 1000.0

    node_data = G.nodes[node_id]
    node_lat = float(node_data["y"])
    node_lon = float(node_data["x"])

    return NearestNodeResult(
        lat=req.lat,
        lon=req.lon,
        method=req.method,
        node_id=node_id,
        node_lat=node_lat,
        node_lon=node_lon,
        distance_m=float(dist),
        time_ms=dt_ms,
    )


@router.post("/nearest-node/batch", response_model=NearestNodeBatchResponse)
def nearest_node_batch(req: NearestNodeBatchRequest):
    """
    Aplica nearest-node a muchos puntos con los métodos solicitados
    (kd y/o bruteforce), y calcula estadísticas de tiempo.
    """
    G, _ = load_graph()

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

            if method == "kd":
                node_id, dist = nearest_node_kd(point.lat, point.lon)
            else:
                node_id, dist = nearest_node_bruteforce(point.lat, point.lon)

            dt_ms = (time.perf_counter() - t0) * 1000.0

            node_data = G.nodes[node_id]
            node_lat = float(node_data["y"])
            node_lon = float(node_data["x"])

            res = NearestNodeResult(
                lat=point.lat,
                lon=point.lon,
                method=method,
                node_id=node_id,
                node_lat=node_lat,
                node_lon=node_lon,
                distance_m=float(dist),
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
