"""Excepciones de dominio de pagos. No conocen HTTP."""


class PaymentError(Exception):
    """Base de los errores de dominio de pagos."""


class PaymentNotFound(PaymentError):
    pass


class InvalidSignature(PaymentError):
    """Firma de integridad/evento inválida: el webhook se rechaza."""


class WebhookReplay(InvalidSignature):
    """Evento de webhook fuera de la ventana de frescura: posible replay.

    Hereda de InvalidSignature → mismo 400 y mensaje genérico hacia el exterior,
    pero es una clase distinta para distinguirlo en los logs del servidor.
    """


class SaleNotPayable(PaymentError):
    """La venta no está en un estado que admita iniciar/confirmar pago."""


class ProviderUnavailable(PaymentError):
    """El proveedor real no puede operar (p. ej. faltan credenciales)."""
