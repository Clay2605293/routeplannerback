# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_basic import router as basic_router
from app.api.routes_nearest import router as nearest_router
from app.api.routes_routing import router as routing_router
from app.api.routes_services import router as services_router
from app.api.routes_demo import router as demo_router

app = FastAPI(
    title="RoutePlanner Backend",
    version="0.1.0",
)

# CORS totalmente abierto
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # <- cualquier dominio
    allow_credentials=False,  # importante: si usas "*", mejor no enviar cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(basic_router)
app.include_router(nearest_router, prefix="/api")
app.include_router(routing_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(demo_router, prefix="/api") 