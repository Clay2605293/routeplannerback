# app/api/routes_demo.py
import random
from typing import List

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.graph.loader import load_graph

router = APIRouter(tags=["demo"])


class RandomPoint(BaseModel):
    node_id: int
    lat: float
    lon: float


class RandomPointsResponse(BaseModel):
    count: int
    points: List[RandomPoint]


@router.get("/demo/random-points", response_model=RandomPointsResponse)
def get_random_points(
    count: int = Query(20, ge=1, le=100, description="Número de puntos aleatorios"),
    seed: int | None = Query(
        None,
        description="Semilla opcional para reproducibilidad en el laboratorio",
    ),
):
    """
    Devuelve `count` nodos aleatorios del grafo como puntos (lat, lon).

    Pensado para el laboratorio del Componente 1:
    - El front llama este endpoint para obtener los puntos.
    - Luego manda estos mismos puntos a /api/nearest-node/batch.
    """
    G, _ = load_graph()  # usa el grafo ya cacheado

    nodes = list(G.nodes(data=True))
    n_total = len(nodes)
    if n_total == 0:
        return RandomPointsResponse(count=0, points=[])

    # Para que en el lab puedas repetir el experimento si quieres
    rng = random.Random(seed)

    # Si piden más de los que hay, limitamos
    real_count = min(count, n_total)

    sampled = rng.sample(nodes, real_count)

    points: List[RandomPoint] = []
    for node_id, data in sampled:
        lat = float(data["y"])
        lon = float(data["x"])
        points.append(
            RandomPoint(
                node_id=node_id,
                lat=lat,
                lon=lon,
            )
        )

    return RandomPointsResponse(count=len(points), points=points)
