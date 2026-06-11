"""Punto de entrada de la API de Tendero."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.routers import (
    analytics,
    auth,
    cash,
    fiscal,
    health,
    inventory,
    invoices,
    payments,
    products,
    sales,
    suppliers,
    webhooks,
)

logger = logging.getLogger("tendero")

_IS_PRODUCTION = settings.app_env == "production"

app = FastAPI(title="Tendero API", version="0.0.0")

# Cabeceras de seguridad en TODA respuesta (nosniff, anti-frame, etc.). HSTS solo en
# producción. Se añade antes que CORS para que también cubra las respuestas de CORS.
app.add_middleware(SecurityHeadersMiddleware, is_production=_IS_PRODUCTION)

# CORS acotado solo al origen del frontend (regla del brief, sección 10).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad para errores NO controlados (no HTTPException).

    Registra la traza COMPLETA del lado del servidor pero devuelve un cuerpo
    genérico al cliente: nunca se filtran trazas ni detalles internos (regla de
    seguridad del brief). Aplica en todos los entornos; en producción es la única
    información que ve el cliente.
    """
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno"})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(cash.router)
app.include_router(sales.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
app.include_router(fiscal.router)
app.include_router(analytics.router)
