# app/api/routes_basic.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"message": "RoutePlanner backend is running"}


@router.get("/health")
def health():
    return {"status": "ok"}
