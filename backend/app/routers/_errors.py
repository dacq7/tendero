"""Traducción de excepciones de dominio (inventario y ventas/caja) a HTTPException.

Centraliza el mapeo para que todos los routers sean consistentes.
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
from app.services.sales_errors import (
    CashSessionAlreadyClosed,
    CashSessionAlreadyOpen,
    CashSessionNotFound,
    EmptySale,
    ForbiddenCashSession,
    InvoiceNotFound,
    NoCashSessionOpen,
    SaleError,
    SaleHasPendingItems,
    SaleNotFound,
)

_STATUS: dict[type[Exception], int] = {
    # Inventario
    SupplierNotFound: status.HTTP_404_NOT_FOUND,
    ProductNotFound: status.HTTP_404_NOT_FOUND,
    DuplicateSku: status.HTTP_409_CONFLICT,
    DuplicateBarcode: status.HTTP_409_CONFLICT,
    InsufficientStock: status.HTTP_409_CONFLICT,
    InvalidQuantity: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidCost: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # Ventas / caja
    SaleNotFound: status.HTTP_404_NOT_FOUND,
    InvoiceNotFound: status.HTTP_404_NOT_FOUND,
    CashSessionNotFound: status.HTTP_404_NOT_FOUND,
    NoCashSessionOpen: status.HTTP_409_CONFLICT,
    CashSessionAlreadyOpen: status.HTTP_409_CONFLICT,
    CashSessionAlreadyClosed: status.HTTP_409_CONFLICT,
    SaleHasPendingItems: status.HTTP_409_CONFLICT,
    ForbiddenCashSession: status.HTTP_403_FORBIDDEN,
    EmptySale: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def http_error(exc: InventoryError | SaleError) -> HTTPException:
    for typ, code in _STATUS.items():
        if isinstance(exc, typ):
            return HTTPException(status_code=code, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
