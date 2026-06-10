"""Excepciones de dominio de pagos. No conocen HTTP."""


class PaymentError(Exception):
    """Base de los errores de dominio de pagos."""


class PaymentNotFound(PaymentError):
    pass


class InvalidSignature(PaymentError):
    """Firma de integridad/evento inválida: el webhook se rechaza."""


class SaleNotPayable(PaymentError):
    """La venta no está en un estado que admita iniciar/confirmar pago."""


class ProviderUnavailable(PaymentError):
    """El proveedor real no puede operar (p. ej. faltan credenciales)."""
