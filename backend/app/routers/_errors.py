"""Traducción de excepciones de dominio de inventario a HTTPException.

Centraliza el mapeo para que todos los routers de inventario sean consistentes.
"""

from fastapi import HTTPException, status

from app.services.inventory_errors import (
    DuplicateBarcode,
    DuplicateSku,
    InsufficientStock,
    InvalidCost,
    InvalidQuantity,
    InventoryError,
    ProductNotFound,
    SupplierNotFound,
)

_STATUS: dict[type[InventoryError], int] = {
    SupplierNotFound: status.HTTP_404_NOT_FOUND,
    ProductNotFound: status.HTTP_404_NOT_FOUND,
    DuplicateSku: status.HTTP_409_CONFLICT,
    DuplicateBarcode: status.HTTP_409_CONFLICT,
    InsufficientStock: status.HTTP_409_CONFLICT,
    InvalidQuantity: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidCost: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def http_error(exc: InventoryError) -> HTTPException:
    for typ, code in _STATUS.items():
        if isinstance(exc, typ):
            return HTTPException(status_code=code, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
