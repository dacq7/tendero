"""Punto de entrada de la API de Tendero."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health

app = FastAPI(title="Tendero API", version="0.0.0")

# CORS acotado solo al origen del frontend (regla del brief, sección 10).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
