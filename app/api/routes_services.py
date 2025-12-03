# app/api/routes_services.py
from fastapi import APIRouter
from typing import List
from app.models import (
    ServiceInfo,
    ServiceRouteRequest,
    ServiceRouteResponse,
    RouteResponse,
    RouteStats,
    LatLon,
)

router = APIRouter()


@router.get("/services", response_model=List[ServiceInfo])
def list_services(type: str | None = None):
    """
    Endpoint dummy: por ahora regresa lista vacía de servicios.
    Luego lo conectamos a OSMnx para gasolineras/llanteras/talleres.
    """
    return []


@router.post("/service-route", response_model=ServiceRouteResponse)
def get_service_route(req: ServiceRouteRequest):
    """
    Endpoint dummy: regresa un servicio ficticio y una ruta recta hacia él.
    Así comprobamos que el backend levanta y la forma del JSON está bien.
    """
    # Servicio “falso” un poco desplazado de la ubicación actual
    dummy_service = ServiceInfo(
        id="srv_dummy",
        type=req.type,
        name="Dummy Service",
        lat=req.location.lat + 0.001,
        lon=req.location.lon + 0.001,
        node_id=1,
    )

    # Ruta “falsa”: solo origen y destino
    dummy_route = RouteResponse(
        origin=req.location,
        destination=LatLon(lat=dummy_service.lat, lon=dummy_service.lon),
        origin_node=1,
        destination_node=2,
        path_nodes=[1, 2],
        geometry=[
            req.location,
            LatLon(lat=dummy_service.lat, lon=dummy_service.lon),
        ],
        distance_m=1000.0,
        travel_time_s=120.0,
        stats=RouteStats(
            algorithm=req.algorithm,
            cost_metric="time",
            expanded_nodes=2,
            time_ms=0.1,
        ),
    )

    return ServiceRouteResponse(
        location=req.location,
        location_node=1,
        service=dummy_service,
        route=dummy_route,
    )
