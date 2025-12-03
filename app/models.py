# app/models.py
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Optional


class LatLon(BaseModel):
    lat: float
    lon: float


AlgorithmName = Literal["bfs", "dfs", "ucs", "iddfs", "astar"]


# --------- NEAREST NODE ---------

class NearestNodeRequest(BaseModel):
    lat: float
    lon: float
    method: Literal["kd", "bruteforce"] = "kd"


class NearestNodeResult(BaseModel):
    lat: float
    lon: float
    method: str
    node_id: int
    node_lat: float
    node_lon: float
    distance_m: float
    time_ms: float


class NearestNodeBatchRequest(BaseModel):
    points: List[LatLon]
    methods: List[Literal["kd", "bruteforce"]] = Field(
        default_factory=lambda: ["kd", "bruteforce"]
    )


class NearestNodeBatchResultItem(BaseModel):
    index: int
    lat: float
    lon: float
    by_method: Dict[str, NearestNodeResult]


class NearestNodeBatchResponse(BaseModel):
    results: List[NearestNodeBatchResultItem]
    summary: Dict[str, Dict[str, float]]


# --------- ROUTES ---------

class RouteRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    algorithm: AlgorithmName = "astar"
    cost_metric: Literal["distance", "time"] = "time"


class RouteStats(BaseModel):
    algorithm: AlgorithmName
    cost_metric: str
    expanded_nodes: int
    time_ms: float


class RouteResponse(BaseModel):
    origin: LatLon
    destination: LatLon
    origin_node: int
    destination_node: int
    path_nodes: List[int]
    geometry: List[LatLon]
    distance_m: float
    travel_time_s: float
    stats: RouteStats


class RouteCompareRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    algorithms: List[AlgorithmName]
    cost_metric: Literal["distance", "time"] = "time"


class RouteCompareResult(BaseModel):
    algorithm: AlgorithmName
    found: bool
    distance_m: Optional[float] = None
    travel_time_s: Optional[float] = None
    expanded_nodes: Optional[int] = None
    time_ms: Optional[float] = None
    is_default_choice: bool = False


class RouteCompareResponse(BaseModel):
    origin_node: int
    destination_node: int
    results: List[RouteCompareResult]


# --------- DEMO TRIPS ---------

class DemoTrip(BaseModel):
    id: str
    client_name: str
    pickup: LatLon
    destination: LatLon


# --------- SERVICES / VORONOI ---------

class ServiceInfo(BaseModel):
    id: str
    type: Literal["gas_station", "tire", "workshop"]
    name: str
    lat: float
    lon: float
    node_id: int


class ServiceRouteRequest(BaseModel):
    location: LatLon
    type: Literal["gas_station", "tire", "workshop"]
    algorithm: AlgorithmName = "astar"


class ServiceRouteResponse(BaseModel):
    location: LatLon
    location_node: int
    service: ServiceInfo
    route: RouteResponse


# Para /api/voronoi/regions (GeoJSON simplificado)
class VoronoiFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    properties: Dict[str, str]
    geometry: Dict[str, object]


class VoronoiFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[VoronoiFeature]
