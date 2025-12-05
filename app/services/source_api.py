# app/services/source_api.py

import os
from typing import List

import httpx

from app.services.models import ServicePoint, ServiceType


# Ajusta esto al endpoint real de tu API de servicios
SERVICES_API_URL = os.getenv("SERVICES_API_URL", "https://example.com/api/services")


def _map_external_type(raw_type: str) -> ServiceType:
    """
    Mapea el tipo que regresa la API externa a nuestro ServiceType interno.
    Ajusta con los valores reales de tu API.
    """
    t = raw_type.lower()
    if "gas" in t or "fuel" in t:
        return "gas_station"
    if "tire" in t or "llantera" in t:
        return "tire_shop"
    # por defecto lo mandamos a workshop
    return "workshop"


def fetch_services_from_external_api() -> List[ServicePoint]:
    """
    Llama a la API externa y traduce la respuesta al modelo interno ServicePoint.
    """
    resp = httpx.get(SERVICES_API_URL, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()

    services: List[ServicePoint] = []

    # Ajusta este bloque según el shape real de tu API
    # Ejemplo: data = {"services": [...]} o data = [...]
    raw_items = data.get("services", data)

    for item in raw_items:
        # NOMBRES DE CAMPOS DE EJEMPLO: cámbialos a los reales
        service_id = str(item["id"])
        name = item.get("name", "Unnamed service")

        raw_type = item.get("type") or item.get("category") or "workshop"
        service_type: ServiceType = _map_external_type(raw_type)

        lat = float(item["lat"])
        lon = float(item["lon"])

        is24h = bool(item.get("is24h", item.get("open_24h", False)))
        has_towing = bool(item.get("hasTowing", item.get("towing", False)))

        services.append(
            ServicePoint(
                id=service_id,
                type=service_type,
                name=name,
                lat=lat,
                lon=lon,
                is24h=is24h,
                hasTowing=has_towing,
            )
        )

    return services
