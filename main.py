# main.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


class RouteRequest(BaseModel):
    origin: tuple[float, float]  # [lat, lon]
    destination: tuple[float, float]


@app.post("/route-demo")
def route_demo(req: RouteRequest):
    # Por ahora es pura simulación; nada de OSM todavía
    return {
        "origin": {"lat": req.origin[0], "lon": req.origin[1]},
        "destination": {"lat": req.destination[0], "lon": req.destination[1]},
        "distance_m": 1234.5,  # dummy
        "stats": {
            "algorithm": "demo",
            "time_ms": 1.23,
        },
    }
