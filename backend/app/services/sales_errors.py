"""Excepciones de dominio de ventas y caja. No conocen HTTP."""


class SaleError(Exception):
    """Base de los errores de dominio de ventas/caja."""


class EmptySale(SaleError):
    pass


class SaleNotFound(SaleError):
    pass


class InvoiceNotFound(SaleError):
    pass


class CashSessionNotFound(SaleError):
    pass


class NoCashSessionOpen(SaleError):
    pass


class CashSessionAlreadyOpen(SaleError):
    pass


class CashSessionAlreadyClosed(SaleError):
    pass


class SaleHasPendingItems(SaleError):
    pass


class ForbiddenCashSession(SaleError):
    """El cajero intenta operar una caja que no es suya."""


class ForbiddenSale(SaleError):
    """El cajero intenta ver una venta/factura que no es suya."""
