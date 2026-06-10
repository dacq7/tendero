"""Excepciones de dominio de facturación electrónica. No conocen HTTP."""


class FiscalError(Exception):
    """Base de los errores de dominio fiscal."""


class EmissionNotFound(FiscalError):
    pass


class InvoiceNotEmittable(FiscalError):
    """La factura no está en un estado que admita emisión (venta no pagada)."""


class NoActiveResolution(FiscalError):
    pass


class ResolutionNotFound(FiscalError):
    pass


class ResolutionExhausted(FiscalError):
    """El rango de la resolución se agotó."""


class ResolutionExpired(FiscalError):
    """La resolución está fuera de vigencia."""


class InvalidResolution(FiscalError):
    pass


class FiscalProviderUnavailable(FiscalError):
    """El PT real no puede operar (faltan credenciales)."""
