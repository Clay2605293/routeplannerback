# fetch_osm_services.py
import json
from pathlib import Path
from typing import Any, Dict, List

import requests

from app.config import OSM_ADDRESS, OSM_DIST_METERS

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = DATA_DIR / "services_osm.json"


def geocode_address(address: str) -> Dict[str, float]:
    """
    Usa Nominatim para geocodificar OSM_ADDRESS y obtener (lat, lon).
    """
    print(f"Geocoding address: {address!r}")
    resp = requests.get(
        NOMINATIM_URL,
        params={
            "q": address,
            "format": "json",
            "limit": 1,
        },
        headers={
            "User-Agent": "RoutePlanner/0.1 (data collection for class project)"
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError(f"Nominatim did not return results for address: {address}")

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    print(f"Geocoded center: lat={lat}, lon={lon}")
    return {"lat": lat, "lon": lon}


def build_overpass_query(lat: float, lon: float, radius_m: int) -> str:
    """
    Construye la consulta Overpass usando 'around' para el radio dado.
    Extrae:
      - amenity=fuel       -> gas_station
      - shop=tyres         -> tire_shop
      - shop=car_repair    -> workshop
    """
    query = f"""
[out:json][timeout:90];
(
  // Gasolineras
  node["amenity"="fuel"](around:{radius_m},{lat},{lon});
  way["amenity"="fuel"](around:{radius_m},{lat},{lon});
  relation["amenity"="fuel"](around:{radius_m},{lat},{lon});

  // Llanteras
  node["shop"="tyres"](around:{radius_m},{lat},{lon});
  way["shop"="tyres"](around:{radius_m},{lat},{lon});
  relation["shop"="tyres"](around:{radius_m},{lat},{lon});

  // Talleres mecánicos
  node["shop"="car_repair"](around:{radius_m},{lat},{lon});
  way["shop"="car_repair"](around:{radius_m},{lat},{lon});
  relation["shop"="car_repair"](around:{radius_m},{lat},{lon});
);
out center;
"""
    return query.strip()


def infer_service_type(tags: Dict[str, Any]) -> str:
    """
    A partir de los tags de OSM, determina si es gas_station, tire_shop o workshop.

    - amenity=fuel       -> gas_station
    - shop=tyres         -> tire_shop
    - shop=car_repair    -> workshop
    (soportamos también amenity=car_repair por si alguien lo usa así)
    """
    amenity = tags.get("amenity")
    shop = tags.get("shop")

    if amenity == "fuel":
        return "gas_station"
    if shop == "tyres":
        return "tire_shop"
    if shop == "car_repair" or amenity == "car_repair":
        return "workshop"

    # Fallback: si llega otro tipo raro, lo tratamos como taller genérico
    return "workshop"


def normalize_element(elem: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte un elemento Overpass (node/way/relation) a un registro simple para JSON.
    La geometría se toma del centro:
      - node: lat/lon del nodo
      - way/relation: lat/lon de 'center' (Overpass lo incluye por 'out center;')
    """
    elem_type = elem.get("type")
    tags = elem.get("tags", {}) or {}

    if elem_type == "node":
        lat = float(elem["lat"])
        lon = float(elem["lon"])
    else:
        center = elem.get("center")
        if not center:
            # Si no hay center, ignoramos este elemento
            raise ValueError("Element without center in Overpass response")
        lat = float(center["lat"])
        lon = float(center["lon"])

    svc_type = infer_service_type(tags)

    name = tags.get("name") or "Unnamed service"

    # Heurísticos simples para flags
    opening_hours = tags.get("opening_hours", "")
    is24h = "24/7" in opening_hours.replace(" ", "")

    # Asumimos asistencia de grúa solo para algunos tags específicos, opcional
    hasTowing = False
    service_tags = [
        tags.get("service"),
        tags.get("description", ""),
        tags.get("note", ""),
    ]
    for txt in service_tags:
        if not txt:
            continue
        low = str(txt).lower()
        if "tow" in low or "grúa" in low or "grua" in low:
            hasTowing = True
            break

    # Etiqueta genérica de área, la puedes pulir a mano si quieres
    area_label = "Guadalajara metro area"

    return {
        "id": f"osm_{elem_type}_{elem['id']}",
        "osm_id": int(elem["id"]),
        "osm_type": elem_type,
        "type": svc_type,
        "name": name,
        "lat": lat,
        "lon": lon,
        "is24h": is24h,
        "hasTowing": hasTowing,
        "areaLabel": area_label,
    }


def main():
    # 1) Geocodificar el centro (mismo que para el grafo)
    center = geocode_address(OSM_ADDRESS)
    lat = center["lat"]
    lon = center["lon"]
    radius_m = int(OSM_DIST_METERS)

    # 2) Construir la consulta Overpass
    query = build_overpass_query(lat, lon, radius_m)
    print("Sending Overpass query...")
    resp = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers={"User-Agent": "RoutePlanner/0.1 (class project)"},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    elements = data.get("elements", [])
    print(f"Received {len(elements)} raw elements from Overpass")

    services: List[Dict[str, Any]] = []
    for elem in elements:
        try:
            svc = normalize_element(elem)
            services.append(svc)
        except Exception as e:
            print(f"Skipping element {elem.get('id')} due to error: {e}")

    print(f"Normalized services count: {len(services)}")

    # 3) Guardar en app/data/services_osm.json
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(services, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(services)} services to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
