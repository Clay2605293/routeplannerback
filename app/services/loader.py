# app/services/loader.py

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "services_osm.json"


@lru_cache(maxsize=1)
def load_osm_services() -> List[Dict[str, Any]]:
    """
    Carga la lista de servicios obtenidos de OSM desde data/services_osm.json.
    Se cachea en memoria para no leerlo en cada request.
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"OSM services file not found: {DATA_PATH}")

    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("services_osm.json must contain a JSON list")

    return data
