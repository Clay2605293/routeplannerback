# app/services/voronoi_loader.py

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "services_voronoi.json"


@lru_cache(maxsize=1)
def load_services_voronoi() -> List[Dict[str, Any]]:
    """
    Carga la lista de celdas Voronoi desde data/services_voronoi.json.
    Estructura esperada (lista de dicts):
      {
        "id": str,
        "osm_id": int,
        "osm_type": str,
        "type": "gas_station" | "tire_shop" | "workshop",
        "name": str,
        "lat": float,
        "lon": float,
        "polygon": [ { "lat": float, "lon": float }, ... ]
      }
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Voronoi services file not found: {DATA_PATH}")

    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("services_voronoi.json must contain a JSON list")

    return data
