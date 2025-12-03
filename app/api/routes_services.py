# app/api/routes_services.py
from fastapi import APIRouter, Query
from typing import List, Optional
import time

from app.models import (
    ServiceInfo,
    ServiceRouteRequest,
    ServiceRouteResponse,
    RouteResponse,
    RouteStats,
    LatLon,
    VoronoiFeatureCollection,
    VoronoiFeature,
)

router = APIRouter()


@router.get("/services", response_model=List[ServiceInfo])
def list_services(type: Optional[str] = Query(default=None)):
    """
    Endpoint dummy: regresa una lista fija de servicios.
    Más adelante se conectará con OSMnx para obtener gasolineras/llanteras/talleres reales.
    """
    all_services = [
        ServiceInfo(
            id="srv_1",
            type="gas_station",
            name="Gasolinera Reforma",
            lat=20.6780,
            lon=-103.3450,
            node_id=555,
        ),
        ServiceInfo(
            id="srv_2",
            type="gas_station",
            name="Gasolinera Central",
            lat=20.6820,
            lon=-103.3505,
            node_id=556,
        ),
        ServiceInfo(
            id="srv_3",
            type="tire",
            name="Llantera López",
            lat=20.6790,
            lon=-103.3480,
            node_id=557,
        ),
    ]

    if type is None:
        return all_services

    return [s for s in all_services if s.type == type]


@router.get("/voronoi/regions", response_model=VoronoiFeatureCollection)
def get_voronoi_regions():
    """
    Versión dummy de la partición de Voronoi.
    Más adelante se construirá con scipy.spatial.Voronoi a partir de los servicios.
    """
    features = [
        VoronoiFeature(
            properties={
                "service_id": "srv_1",
                "type": "gas_station",
                "name": "Gasolinera Reforma",
            },
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [-103.3460, 20.6770],
                        [-103.3440, 20.6775],
                        [-103.3430, 20.6790],
                        [-103.3460, 20.6800],
                        [-103.3460, 20.6770],
                    ]
                ],
            },
        )
    ]

    return VoronoiFeatureCollection(features=features)


@router.post("/service-route", response_model=ServiceRouteResponse)
def get_service_route(req: ServiceRouteRequest):
    """
    Endpoint dummy: regresa un servicio "más cercano" ficticio
    y una ruta recta hacia él.
    Después usaremos Voronoi + SimpleAI aquí.
    """
    t0 = time.perf_counter()

    # Servicio ficticio
    dummy_service = ServiceInfo(
        id="srv_dummy",
        type=req.type,
        name="Dummy Service",
        lat=req.location.lat + 0.001,
        lon=req.location.lon + 0.001,
        node_id=1,
    )

    # Ruta ficticia: solo origen y destino
    origin_node = 1
    destination_node = 2
    path_nodes = [origin_node, destination_node]

    geometry = [
        req.location,
        LatLon(lat=dummy_service.lat, lon=dummy_service.lon),
    ]

    distance_m = 1000.0
    travel_time_s = 120.0

    dt_ms = (time.perf_counter() - t0) * 1000.0

    stats = RouteStats(
        algorithm=req.algorithm,
        cost_metric="time",
        expanded_nodes=len(path_nodes),
        time_ms=dt_ms,
    )

    route = RouteResponse(
        origin=req.location,
        destination=LatLon(lat=dummy_service.lat, lon=dummy_service.lon),
        origin_node=origin_node,
        destination_node=destination_node,
        path_nodes=path_nodes,
        geometry=geometry,
        distance_m=distance_m,
        travel_time_s=travel_time_s,
        stats=stats,
    )

    return ServiceRouteResponse(
        location=req.location,
        location_node=origin_node,
        service=dummy_service,
        route=route,
    )
