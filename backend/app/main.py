"""Punto de entrada de la API de Tendero."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    auth,
    cash,
    health,
    inventory,
    invoices,
    payments,
    products,
    sales,
    suppliers,
    webhooks,
)

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
app.include_router(auth.router)
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(cash.router)
app.include_router(sales.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
