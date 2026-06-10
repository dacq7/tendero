"""Aritmética de dinero compartida. Enteros siempre (centavos / milésimas)."""


def round_half_up(numerador: int, denominador: int) -> int:
    """División entera con redondeo half-up determinista (denominador > 0).

    Determinista (no el round() bancario de Python) para que los cálculos de
    dinero sean exactos y reproducibles en tests.
    """
    return (numerador + denominador // 2) // denominador
