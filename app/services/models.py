# app/services/models.py

from typing import Literal, Optional
from pydantic import BaseModel


ServiceType = Literal["gas_station", "tire_shop", "workshop"]


class ServicePoint(BaseModel):
    """
    Representa un punto de servicio (gasolinera, llantera, taller).
    """
    id: str
    type: ServiceType
    name: str
    lat: float
    lon: float

    # Flags opcionales que suelen venir en tu API
    is24h: bool = False
    hasTowing: bool = False

    # Enriquecidos en backend
    node_id: Optional[int] = None   # nodo en el grafo más cercano
    x: Optional[float] = None       # coords proyectadas (G_proj)
    y: Optional[float] = None
