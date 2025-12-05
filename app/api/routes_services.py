# app/api/routes_services.py

from typing import List, Literal, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.loader import load_osm_services
from app.graph.kdtree import nearest_node_kd
from app.graph.loader import load_graph
from app.graph.routing import run_search, compute_path_metrics
from app.services.voronoi_loader import load_services_voronoi

router = APIRouter(tags=["services"])


ServiceType = Literal["gas_station", "tire_shop", "workshop", "any"]


class ServiceBase(BaseModel):
    id: str
    osm_id: int
    osm_type: str
    type: Literal["gas_station", "tire_shop", "workshop"]
    name: str
    lat: float
    lon: float
    is24h: bool
    hasTowing: bool
    areaLabel: Optional[str] = None


class ServiceWithMetrics(ServiceBase):
    distanceKm: float
    estimatedTimeMin: float


class ServicesNearbyResponse(BaseModel):
    services: List[ServiceWithMetrics]


class EmergencyRouteRequest(BaseModel):
    position: Dict[str, float]  # { "lat": ..., "lon": ... }
    service_type: ServiceType = "any"


class RouteCoord(BaseModel):
    lat: float
    lon: float

class ServiceVoronoiCell(BaseModel):
    id: str
    osm_id: int
    osm_type: str
    type: Literal["gas_station", "tire_shop", "workshop"]
    name: str
    lat: float
    lon: float
    polygon: List[RouteCoord]


class ServicesVoronoiResponse(BaseModel):
    cells: List[ServiceVoronoiCell]



class EmergencyRouteServiceInfo(ServiceBase):
    distanceKm: float
    estimatedTimeMin: float


class EmergencyRouteResponse(BaseModel):
    service: EmergencyRouteServiceInfo
    algorithm: str
    cost_metric: str
    found: bool
    distance_m: float
    travel_time_s: float
    time_ms: float
    path_nodes: List[int]
    path_coords: List[RouteCoord]


def _type_label(svc_type: str) -> str:
    if svc_type == "gas_station":
        return "Gas station"
    if svc_type == "tire_shop":
        return "Tire shop"
    if svc_type == "workshop":
        return "Workshop"
    return "Service"


def _filter_services(
    all_services: List[Dict[str, Any]],
    svc_type: ServiceType,
) -> List[Dict[str, Any]]:
    if svc_type == "any":
        return all_services
    return [s for s in all_services if s.get("type") == svc_type]


def _compute_route_metrics(
    driver_lat: float,
    driver_lon: float,
    service_lat: float,
    service_lon: float,
) -> Optional[Dict[str, Any]]:
    """
    Convierte driver y servicio a nodos del grafo y calcula la ruta óptima
    con A* usando 'time' como métrica.
    Regresa None si no se encuentra ruta.
    """
    driver_node, _ = nearest_node_kd(driver_lat, driver_lon)
    service_node, _ = nearest_node_kd(service_lat, service_lon)

    search_res = run_search(
        origin_node=driver_node,
        goal_node=service_node,
        algorithm="astar",
        cost_metric="time",
    )

    if not search_res["found"]:
        return None

    metrics = compute_path_metrics(search_res["path_nodes"])
    distance_m = metrics["distance_m"]
    travel_time_s = metrics["travel_time_s"]

    return {
        "origin_node": driver_node,
        "destination_node": service_node,
        "search": search_res,
        "distance_m": distance_m,
        "travel_time_s": travel_time_s,
    }

def _point_in_polygon(lat: float, lon: float, polygon: List[Dict[str, float]]) -> bool:
    """
    Test simple de punto en polígono (ray casting).
    polygon: lista de dicts { "lat": ..., "lon": ... } en orden.
    """
    x = lon
    y = lat
    inside = False
    n = len(polygon)
    if n < 3:
        return False

    for i in range(n):
        j = (i - 1) % n
        xi = polygon[i]["lon"]
        yi = polygon[i]["lat"]
        xj = polygon[j]["lon"]
        yj = polygon[j]["lat"]

        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
        )
        if intersect:
            inside = not inside

    return inside


@router.get("/services/nearby", response_model=ServicesNearbyResponse)
def get_services_nearby(
    driver_lat: float = Query(...),
    driver_lon: float = Query(...),
    service_type: ServiceType = Query("any"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Regresa servicios cercanos al chofer, ordenados por distancia de ruta
    (usando A* sobre el grafo vial).

    - driver_lat, driver_lon: posición del chofer.
    - service_type: gas_station | tire_shop | workshop | any
    - limit: máximo de servicios en la respuesta.
    """
    all_services = load_osm_services()
    candidates = _filter_services(all_services, service_type)

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="No hay servicios disponibles para ese tipo.",
        )

    results: List[ServiceWithMetrics] = []

    for svc in candidates:
        route_info = _compute_route_metrics(
            driver_lat=driver_lat,
            driver_lon=driver_lon,
            service_lat=svc["lat"],
            service_lon=svc["lon"],
        )
        if route_info is None:
            continue

        distance_km = route_info["distance_m"] / 1000.0
        duration_min = route_info["travel_time_s"] / 60.0

        svc_with_metrics = ServiceWithMetrics(
            id=str(svc["id"]),
            osm_id=int(svc["osm_id"]),
            osm_type=str(svc["osm_type"]),
            type=svc["type"],
            name=svc["name"],
            lat=float(svc["lat"]),
            lon=float(svc["lon"]),
            is24h=bool(svc.get("is24h", False)),
            hasTowing=bool(svc.get("hasTowing", False)),
            areaLabel=svc.get("areaLabel"),
            distanceKm=distance_km,
            estimatedTimeMin=duration_min,
        )
        results.append(svc_with_metrics)

    if not results:
        raise HTTPException(
            status_code=500,
            detail="No se pudo calcular rutas a ningún servicio.",
        )

    # Ordenamos por distancia
    results.sort(key=lambda s: s.distanceKm)

    # Limitamos
    results = results[:limit]

    return ServicesNearbyResponse(services=results)


@router.post("/emergency/nearest-service-route", response_model=EmergencyRouteResponse)
def emergency_nearest_service_route(req: EmergencyRouteRequest):
    """
    Dada una posición en el mapa, determina el servicio más cercano según tipo,
    y regresa la ruta óptima (A* + 'time') hacia ese servicio.
    """
    all_services = load_osm_services()
    candidates = _filter_services(all_services, req.service_type)

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="No hay servicios disponibles para ese tipo.",
        )

    driver_lat = req.position["lat"]
    driver_lon = req.position["lon"]

    best: Optional[Dict[str, Any]] = None

    for svc in candidates:
        route_info = _compute_route_metrics(
            driver_lat=driver_lat,
            driver_lon=driver_lon,
            service_lat=svc["lat"],
            service_lon=svc["lon"],
        )
        if route_info is None:
            continue

        distance_km = route_info["distance_m"] / 1000.0
        duration_min = route_info["travel_time_s"] / 60.0

        candidate = {
            "svc": svc,
            "route_info": route_info,
            "distance_km": distance_km,
            "duration_min": duration_min,
        }

        if best is None or distance_km < best["distance_km"]:
            best = candidate

    if best is None:
        raise HTTPException(
            status_code=500,
            detail="No se pudo encontrar ruta a ningún servicio.",
        )

    svc = best["svc"]
    route_info = best["route_info"]

    # Construimos path_coords igual que en /api/route
    G, _ = load_graph()
    path_nodes = route_info["search"]["path_nodes"]
    path_coords = []
    for node_id in path_nodes:
        data = G.nodes[node_id]
        path_coords.append(
            RouteCoord(
                lat=float(data["y"]),
                lon=float(data["x"]),
            )
        )

    svc_info = EmergencyRouteServiceInfo(
        id=str(svc["id"]),
        osm_id=int(svc["osm_id"]),
        osm_type=str(svc["osm_type"]),
        type=svc["type"],
        name=svc["name"],
        lat=float(svc["lat"]),
        lon=float(svc["lon"]),
        is24h=bool(svc.get("is24h", False)),
        hasTowing=bool(svc.get("hasTowing", False)),
        areaLabel=svc.get("areaLabel"),
        distanceKm=best["distance_km"],
        estimatedTimeMin=best["duration_min"],
    )

    return EmergencyRouteResponse(
        service=svc_info,
        algorithm="astar",
        cost_metric="time",
        found=True,
        distance_m=route_info["distance_m"],
        travel_time_s=route_info["travel_time_s"],
        time_ms=route_info["search"]["time_ms"],
        path_nodes=path_nodes,
        path_coords=path_coords,
    )

@router.get("/services/voronoi", response_model=ServicesVoronoiResponse)
def get_services_voronoi(
    service_type: ServiceType = Query("any"),
):
    """
    Regresa las celdas Voronoi de los servicios (para que el front las pinte).
    Se puede filtrar por tipo: gas_station | tire_shop | workshop | any.
    """
    cells_raw = load_services_voronoi()

    if service_type != "any":
        cells_raw = [c for c in cells_raw if c.get("type") == service_type]

    cells: List[ServiceVoronoiCell] = []
    for c in cells_raw:
        polygon_coords = [
            RouteCoord(lat=float(p["lat"]), lon=float(p["lon"]))
            for p in c["polygon"]
        ]
        cell = ServiceVoronoiCell(
            id=str(c["id"]),
            osm_id=int(c["osm_id"]),
            osm_type=str(c["osm_type"]),
            type=c["type"],
            name=c["name"],
            lat=float(c["lat"]),
            lon=float(c["lon"]),
            polygon=polygon_coords,
        )
        cells.append(cell)

    return ServicesVoronoiResponse(cells=cells)


@router.post(
    "/emergency/nearest-service-voronoi",
    response_model=EmergencyRouteResponse,
)
def emergency_nearest_service_voronoi(req: EmergencyRouteRequest):
    """
    Variante del servicio de emergencia que:
      1) Usa la partición de Voronoi para decidir qué servicio "posee" el punto.
      2) Calcula la ruta óptima (A* + 'time') hacia ese servicio.

    Si el punto cae fuera de todas las celdas (por regiones infinitas o precisión),
    se hace fallback al comportamiento de /emergency/nearest-service-route.
    """
    all_cells = load_services_voronoi()

    # Filtro por tipo, si aplica
    if req.service_type != "any":
        all_cells = [c for c in all_cells if c.get("type") == req.service_type]

    if not all_cells:
        raise HTTPException(
            status_code=404,
            detail="No hay servicios disponibles para ese tipo (Voronoi).",
        )

    lat = req.position["lat"]
    lon = req.position["lon"]

    chosen_cell = None

    for c in all_cells:
        polygon = c.get("polygon", [])
        if not polygon:
            continue
        if _point_in_polygon(lat, lon, polygon):
            chosen_cell = c
            break

    # Fallback: si no caímos en ninguna celda, usamos la lógica anterior
    if chosen_cell is None:
        # Reusamos la lógica de emergency_nearest_service_route
        # pero llamándola internamente sería más limpio; aquí la replicamos rápido:
        all_services = load_osm_services()
        candidates = _filter_services(all_services, req.service_type)

        if not candidates:
            raise HTTPException(
                status_code=404,
                detail="No hay servicios disponibles para ese tipo.",
            )

        best = None
        for svc in candidates:
            route_info = _compute_route_metrics(
                driver_lat=lat,
                driver_lon=lon,
                service_lat=svc["lat"],
                service_lon=svc["lon"],
            )
            if route_info is None:
                continue

            distance_km = route_info["distance_m"] / 1000.0
            duration_min = route_info["travel_time_s"] / 60.0

            candidate = {
                "svc": svc,
                "route_info": route_info,
                "distance_km": distance_km,
                "duration_min": duration_min,
            }
            if best is None or distance_km < best["distance_km"]:
                best = candidate

        if best is None:
            raise HTTPException(
                status_code=500,
                detail="No se pudo encontrar ruta a ningún servicio (fallback).",
            )

        svc = best["svc"]
        route_info = best["route_info"]

    else:
        # Tenemos celda Voronoi; la tratamos como servicio elegido
        svc = {
            "id": chosen_cell["id"],
            "osm_id": chosen_cell["osm_id"],
            "osm_type": chosen_cell["osm_type"],
            "type": chosen_cell["type"],
            "name": chosen_cell["name"],
            "lat": chosen_cell["lat"],
            "lon": chosen_cell["lon"],
            "is24h": False,
            "hasTowing": False,
            "areaLabel": "Voronoi region",
        }
        route_info = _compute_route_metrics(
            driver_lat=lat,
            driver_lon=lon,
            service_lat=svc["lat"],
            service_lon=svc["lon"],
        )
        if route_info is None:
            raise HTTPException(
                status_code=500,
                detail="No se pudo calcular ruta al servicio elegido por Voronoi.",
            )

        distance_km = route_info["distance_m"] / 1000.0
        duration_min = route_info["travel_time_s"] / 60.0

        best = {
            "svc": svc,
            "route_info": route_info,
            "distance_km": distance_km,
            "duration_min": duration_min,
        }

    # Armamos respuesta (igual que en emergency_nearest_service_route)
    G, _ = load_graph()
    path_nodes = route_info["search"]["path_nodes"]
    path_coords = []
    for node_id in path_nodes:
        data = G.nodes[node_id]
        path_coords.append(
            RouteCoord(
                lat=float(data["y"]),
                lon=float(data["x"]),
            )
        )

    svc_info = EmergencyRouteServiceInfo(
        id=str(svc["id"]),
        osm_id=int(svc["osm_id"]),
        osm_type=str(svc["osm_type"]),
        type=svc["type"],
        name=svc["name"],
        lat=float(svc["lat"]),
        lon=float(svc["lon"]),
        is24h=bool(svc.get("is24h", False)),
        hasTowing=bool(svc.get("hasTowing", False)),
        areaLabel=svc.get("areaLabel"),
        distanceKm=best["distance_km"],
        estimatedTimeMin=best["duration_min"],
    )

    return EmergencyRouteResponse(
        service=svc_info,
        algorithm="astar",
        cost_metric="time",
        found=True,
        distance_m=route_info["distance_m"],
        travel_time_s=route_info["travel_time_s"],
        time_ms=route_info["search"]["time_ms"],
        path_nodes=path_nodes,
        path_coords=path_coords,
    )
