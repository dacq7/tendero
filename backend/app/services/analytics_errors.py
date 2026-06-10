"""Excepciones de dominio de analítica. No conocen HTTP."""


class AnalyticsError(Exception):
    """Base de los errores de dominio de analítica."""


class InvalidDateRange(AnalyticsError):
    """El rango de fechas es inválido (desde > hasta)."""
