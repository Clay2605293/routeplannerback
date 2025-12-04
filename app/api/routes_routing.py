# app/api/routes_routing.py

import random
from typing import List, Literal, Optional, Dict, Any, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.graph.loader import load_graph
from app.graph.kdtree import nearest_node_kd
from app.graph.routing import (
    run_search,
    compute_path_metrics,
    AlgorithmName,
    CostMetric,
)

router = APIRouter(tags=["routing"])


# ---------- Modelos Pydantic básicos ----------

class LatLon(BaseModel):
    lat: float
    lon: float


class DemoPair(BaseModel):
    id: str
    origin: LatLon
    destination: LatLon
    distance_m: float


class RoutePairsResponse(BaseModel):
    short: List[DemoPair]
    medium: List[DemoPair]
    long: List[DemoPair]


class PairInput(BaseModel):
    id: Optional[str] = None
    origin: LatLon
    destination: LatLon


class EvaluateBatchRequest(BaseModel):
    pairs: List[PairInput]
    algorithm: AlgorithmName
    cost_metric: CostMetric = "time"


class EvaluateResultItem(BaseModel):
    id: str
    origin_node: int
    destination_node: int
    found: bool
    distance_m: Optional[float] = None
    travel_time_s: Optional[float] = None
    time_ms: float


class EvaluateBatchResponse(BaseModel):
    algorithm: AlgorithmName
    cost_metric: CostMetric
    results: List[EvaluateResultItem]
    summary: Dict[str, Optional[float]]


# ---------- Modelos para /api/route (ruta única) ----------

class RouteRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    cost_metric: CostMetric = "time"
    algorithm: AlgorithmName = "astar"


class RoutePathCoord(BaseModel):
    lat: float
    lon: float


class RouteResponse(BaseModel):
    algorithm: AlgorithmName
    cost_metric: CostMetric
    found: bool
    origin_node: Optional[int] = None
    destination_node: Optional[int] = None
    distance_m: Optional[float] = None
    travel_time_s: Optional[float] = None
    time_ms: float
    path_nodes: List[int] = []
    path_coords: List[RoutePathCoord] = []


# ---------- Modelos para modo chofer (/api/demo/trips) ----------

class DemoTrip(BaseModel):
    id: str

    clientName: str
    pickupLabel: str
    dropoffLabel: str

    lengthCategory: Literal["short", "medium", "long"]
    status: Literal["pending", "in_progress", "completed"]

    driverLat: float
    driverLon: float
    clientLat: float
    clientLon: float
    destinationLat: float
    destinationLon: float

    pickupDistanceKm: float
    pickupDurationMin: float
    dropoffDistanceKm: float
    dropoffDurationMin: float
    totalDistanceKm: float
    totalDurationMin: float

    algorithmUsed: Literal["astar"] = "astar"


class DemoTripsResponse(BaseModel):
    trips: List[DemoTrip]


# ---------- Utils internos para el lab ----------

SHORT_MAX = 1000.0   # < 1000 m
MID_MIN = 1000.0     # >= 1000 m
MID_MAX = 5000.0     # <= 5000 m
LONG_MIN = 5000.0    # > 5000 m

NUM_PER_BUCKET = 5
MAX_TRIES = 50000


@router.get("/demo/route-pairs", response_model=RoutePairsResponse)
def get_demo_route_pairs(seed: Optional[int] = None):
    """
    Genera 15 parejas de nodos (5 short, 5 medium, 5 long) usando distancias
    euclidianas en el plano proyectado.
    Sirve como insumo para el laboratorio de algoritmos.
    """
    G, G_proj = load_graph()

    if seed is not None:
        random.seed(seed)

    # Nodos con lat/lon desde G (original) y proyección desde G_proj
    nodes = list(G.nodes(data=True))
    proj_data = dict(G_proj.nodes(data=True))

    short_pairs = []
    mid_pairs = []
    long_pairs = []

    seen_pairs = set()
    tries = 0

    while tries < MAX_TRIES:
        tries += 1

        if (
            len(short_pairs) >= NUM_PER_BUCKET
            and len(mid_pairs) >= NUM_PER_BUCKET
            and len(long_pairs) >= NUM_PER_BUCKET
        ):
            break

        (id_a, data_a) = random.choice(nodes)
        (id_b, data_b) = random.choice(nodes)

        if id_a == id_b:
            continue

        key = tuple(sorted((id_a, id_b)))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        proj_a = proj_data.get(id_a)
        proj_b = proj_data.get(id_b)
        if proj_a is None or proj_b is None:
            continue

        ax, ay = proj_a["x"], proj_a["y"]
        bx, by = proj_b["x"], proj_b["y"]
        dx = ax - bx
        dy = ay - by
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < SHORT_MAX and len(short_pairs) < NUM_PER_BUCKET:
            short_pairs.append((id_a, data_a, id_b, data_b, dist))
        elif MID_MIN <= dist <= MID_MAX and len(mid_pairs) < NUM_PER_BUCKET:
            mid_pairs.append((id_a, data_a, id_b, data_b, dist))
        elif dist > LONG_MIN and len(long_pairs) < NUM_PER_BUCKET:
            long_pairs.append((id_a, data_a, id_b, data_b, dist))

    def pack_pairs(bucket_name: str, pairs) -> List[DemoPair]:
        packed: List[DemoPair] = []
        for idx, (id_a, data_a, id_b, data_b, dist) in enumerate(
            sorted(pairs, key=lambda p: p[4])
        ):
            lat_a, lon_a = data_a["y"], data_a["x"]
            lat_b, lon_b = data_b["y"], data_b["x"]
            packed.append(
                DemoPair(
                    id=f"{bucket_name}_{idx + 1}",
                    origin=LatLon(lat=lat_a, lon=lon_a),
                    destination=LatLon(lat=lat_b, lon=lon_b),
                    distance_m=float(dist),
                )
            )
        return packed

    if not short_pairs or not mid_pairs or not long_pairs:
        raise HTTPException(
            status_code=500,
            detail="No se pudieron generar suficientes parejas en alguna categoría. "
                   "Intenta de nuevo o reduce los umbrales.",
        )

    return RoutePairsResponse(
        short=pack_pairs("short", short_pairs),
        medium=pack_pairs("medium", mid_pairs),
        long=pack_pairs("long", long_pairs),
    )


@router.post(
    "/demo/route-evaluate-batch",
    response_model=EvaluateBatchResponse,
)
def demo_route_evaluate_batch(req: EvaluateBatchRequest):
    """
    Evalúa UN algoritmo (BFS, DFS, UCS, IDDFS, A*) sobre varias parejas de
    origen/destino. Sirve para el laboratorio del Componente 2.

    Flujo:
      - Convierte lat/lon -> nodo más cercano (KD-tree).
      - Ejecuta el algoritmo indicado sobre cada pareja.
      - Calcula distancia y tiempo físico de la ruta.
      - Regresa resultados individuales y un resumen promedio.
    """
    if not req.pairs:
        raise HTTPException(status_code=400, detail="Debes enviar al menos una pareja.")

    results: List[EvaluateResultItem] = []

    for idx, pair in enumerate(req.pairs):
        pair_id = pair.id or f"pair_{idx + 1}"

        origin_node, _ = nearest_node_kd(pair.origin.lat, pair.origin.lon)
        dest_node, _ = nearest_node_kd(pair.destination.lat, pair.destination.lon)

        search_res = run_search(
            origin_node=origin_node,
            goal_node=dest_node,
            algorithm=req.algorithm,
            cost_metric=req.cost_metric,
        )

        if search_res["found"]:
            metrics = compute_path_metrics(search_res["path_nodes"])
            distance_m = metrics["distance_m"]
            travel_time_s = metrics["travel_time_s"]
        else:
            distance_m = None
            travel_time_s = None

        item = EvaluateResultItem(
            id=pair_id,
            origin_node=origin_node,
            destination_node=dest_node,
            found=search_res["found"],
            distance_m=distance_m,
            travel_time_s=travel_time_s,
            time_ms=search_res["time_ms"],
        )
        results.append(item)

    # Resumen (solo sobre rutas encontradas)
    found_results = [r for r in results if r.found and r.distance_m is not None]

    if found_results:
        avg_distance = sum(r.distance_m for r in found_results) / len(found_results)
        avg_time_s = sum(r.travel_time_s for r in found_results) / len(found_results)
        avg_time_ms = sum(r.time_ms for r in found_results) / len(found_results)
    else:
        avg_distance = None
        avg_time_s = None
        avg_time_ms = None

    summary = {
        "count": float(len(results)),
        "found_count": float(len(found_results)),
        "avg_distance_m": avg_distance,
        "avg_travel_time_s": avg_time_s,
        "avg_time_ms": avg_time_ms,
    }

    return EvaluateBatchResponse(
        algorithm=req.algorithm,
        cost_metric=req.cost_metric,
        results=results,
        summary=summary,
    )


# ---------- Ruta única para el mapa ----------

@router.post("/route", response_model=RouteResponse)
def compute_route(req: RouteRequest):
    """
    Calcula una ruta entre origin y destination usando el grafo OSM.
    Devuelve:
      - distance_m, travel_time_s
      - path_nodes: ids de nodos
      - path_coords: lat/lon de cada nodo (para dibujar polilínea en el mapa)
    """
    origin_node, _ = nearest_node_kd(req.origin.lat, req.origin.lon)
    dest_node, _ = nearest_node_kd(req.destination.lat, req.destination.lon)

    search_res = run_search(
        origin_node=origin_node,
        goal_node=dest_node,
        algorithm=req.algorithm,
        cost_metric=req.cost_metric,
    )

    if not search_res["found"]:
        return RouteResponse(
            algorithm=req.algorithm,
            cost_metric=req.cost_metric,
            found=False,
            origin_node=origin_node,
            destination_node=dest_node,
            distance_m=None,
            travel_time_s=None,
            time_ms=search_res["time_ms"],
            path_nodes=[],
            path_coords=[],
        )

    path_nodes = search_res["path_nodes"]
    metrics = compute_path_metrics(path_nodes)

    G, _ = load_graph()
    coords: List[RoutePathCoord] = []
    for n in path_nodes:
        data = G.nodes[n]
        coords.append(
            RoutePathCoord(
                lat=float(data["y"]),
                lon=float(data["x"]),
            )
        )

    return RouteResponse(
        algorithm=req.algorithm,
        cost_metric=req.cost_metric,
        found=True,
        origin_node=origin_node,
        destination_node=dest_node,
        distance_m=metrics["distance_m"],
        travel_time_s=metrics["travel_time_s"],
        time_ms=search_res["time_ms"],
        path_nodes=path_nodes,
        path_coords=coords,
    )


# ---------- Modo chofer: demo trips ----------

@router.get("/demo/trips", response_model=DemoTripsResponse)
def get_demo_trips(seed: Optional[int] = None):
    """
    Genera 15 viajes de demostración para el modo chofer.
    Usa:
      - /demo/route-pairs (lógica interna) para definir cliente/destino.
      - Un "driver base" fijo (nodo cercano al centro de los pickups).
      - A* como algoritmo por defecto para calcular:
          - base -> cliente
          - cliente -> destino
    """
    pairs_resp = get_demo_route_pairs(seed=seed)

    all_pairs_with_cat: List[Tuple[DemoPair, str]] = []
    for p in pairs_resp.short:
        all_pairs_with_cat.append((p, "short"))
    for p in pairs_resp.medium:
        all_pairs_with_cat.append((p, "medium"))
    for p in pairs_resp.long:
        all_pairs_with_cat.append((p, "long"))

    if not all_pairs_with_cat:
        raise HTTPException(status_code=500, detail="No hay parejas de demo disponibles.")

    # Centro aproximado de todos los pickups
    all_lats = [p.origin.lat for (p, _) in all_pairs_with_cat]
    all_lons = [p.origin.lon for (p, _) in all_pairs_with_cat]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    # Nodo base del chofer
    driver_base_node, _ = nearest_node_kd(center_lat, center_lon)

    G, _ = load_graph()
    base_data = G.nodes[driver_base_node]
    driver_base_lat = float(base_data["y"])
    driver_base_lon = float(base_data["x"])

    client_names = [
        "María López", "Juan Pérez", "Luis Hernández", "Ana Torres",
        "Carlos García", "Sofía Ramírez", "Pedro Sánchez", "Elena Cruz",
        "Fernando Díaz", "Laura Martínez", "Miguel Ortega", "Paola Gómez",
        "Jorge Romero", "Daniela Flores", "Ricardo Herrera",
    ]
    pickup_labels = [
        "Cerca de Tec Campus", "Glorieta cercana", "Plaza pequeña",
        "Zona residencial", "Esquina transitada", "Parque cercano",
        "Centro comercial", "Oficina", "Restaurante", "Café",
        "Tienda de conveniencia", "Farmacia", "Banco", "Parada de bus",
        "Calle tranquila",
    ]
    dropoff_labels = [
        "Destino 1", "Destino 2", "Destino 3", "Destino 4", "Destino 5",
        "Oficina destino", "Centro comercial destino", "Casa del cliente",
        "Restaurante destino", "Escuela", "Hospital", "Hotel", "Gimnasio",
        "Parque destino", "Club deportivo",
    ]

    trips: List[DemoTrip] = []

    for idx, (pair, length_cat) in enumerate(all_pairs_with_cat):
        client = pair.origin
        dest = pair.destination

        client_node, _ = nearest_node_kd(client.lat, client.lon)
        dest_node, _ = nearest_node_kd(dest.lat, dest.lon)

        # Ruta base -> cliente
        res_pickup = run_search(
            origin_node=driver_base_node,
            goal_node=client_node,
            algorithm="astar",
            cost_metric="time",
        )

        # Ruta cliente -> destino
        res_dropoff = run_search(
            origin_node=client_node,
            goal_node=dest_node,
            algorithm="astar",
            cost_metric="time",
        )

        if res_pickup["found"]:
            m1 = compute_path_metrics(res_pickup["path_nodes"])
            pickup_km = m1["distance_m"] / 1000.0
            pickup_min = m1["travel_time_s"] / 60.0
        else:
            pickup_km = 0.0
            pickup_min = 0.0

        if res_dropoff["found"]:
            m2 = compute_path_metrics(res_dropoff["path_nodes"])
            dropoff_km = m2["distance_m"] / 1000.0
            dropoff_min = m2["travel_time_s"] / 60.0
        else:
            dropoff_km = 0.0
            dropoff_min = 0.0

        total_km = pickup_km + dropoff_km
        total_min = pickup_min + dropoff_min

        if res_pickup["found"] and res_dropoff["found"]:
            status: Literal["pending", "in_progress", "completed"] = "completed"
        else:
            status = "pending"

        name = client_names[idx % len(client_names)]
        pickup_label = pickup_labels[idx % len(pickup_labels)]
        dropoff_label = dropoff_labels[idx % len(dropoff_labels)]

        trips.append(
            DemoTrip(
                id=f"TRIP-{idx + 1:03d}",
                clientName=name,
                pickupLabel=pickup_label,
                dropoffLabel=dropoff_label,
                lengthCategory=length_cat,  # short/medium/long del par
                status=status,
                driverLat=driver_base_lat,
                driverLon=driver_base_lon,
                clientLat=client.lat,
                clientLon=client.lon,
                destinationLat=dest.lat,
                destinationLon=dest.lon,
                pickupDistanceKm=pickup_km,
                pickupDurationMin=pickup_min,
                dropoffDistanceKm=dropoff_km,
                dropoffDurationMin=dropoff_min,
                totalDistanceKm=total_km,
                totalDurationMin=total_min,
                algorithmUsed="astar",
            )
        )

    return DemoTripsResponse(trips=trips)
