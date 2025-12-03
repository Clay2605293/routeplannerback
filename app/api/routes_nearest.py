# app/api/routes_nearest.py
from fastapi import APIRouter
from app.models import NearestNodeRequest, NearestNodeResult

router = APIRouter()

@router.post("/nearest-node", response_model=NearestNodeResult)
def nearest_node(req: NearestNodeRequest):
    # Aquí llamas a las funciones de KD-tree o brute force
    # Por ahora regresa algo dummy para probar que el endpoint funciona
    return NearestNodeResult(
        lat=req.lat,
        lon=req.lon,
        method=req.method,
        node_id=123,
        node_lat=req.lat,
        node_lon=req.lon,
        distance_m=0.0,
        time_ms=0.1,
    )
