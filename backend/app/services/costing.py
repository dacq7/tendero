"""Matemática de dinero del inventario: costeo y márgenes. Funciones PURAS.

Todo en enteros: precios en centavos COP, cantidades en milésimas de unidad
(1000 = 1 unidad). El redondeo al centavo es half-up determinista (ver
services/money.py), para que los tests sean exactos y reproducibles.
"""

from app.services.money import round_half_up


def margin_centavos(precio_venta_centavos: int, precio_costo_centavos: int) -> int:
    """Margen unitario en centavos (puede ser negativo si se vende a pérdida)."""
    return precio_venta_centavos - precio_costo_centavos


def margin_bps(precio_venta_centavos: int, precio_costo_centavos: int) -> int | None:
    """Margen sobre el precio de venta en PUNTOS BÁSICOS (entero, 10000 = 100%).

    Enteros para respetar el invariante 'dinero nunca float' (igual que
    IVA_RATE_BPS). El frontend lo formatea a %. None si no hay precio de venta.
    """
    if precio_venta_centavos <= 0:
        return None
    margen = precio_venta_centavos - precio_costo_centavos
    return margen * 10000 // precio_venta_centavos


def weighted_average_cost(
    stock_actual_milesimas: int,
    costo_actual_centavos: int,
    cantidad_entrada_milesimas: int,
    costo_entrada_centavos: int,
) -> int:
    """Costo promedio ponderado (CMP) tras una entrada, en centavos por unidad.

    Pondera por cantidades (milésimas); el factor 1000 se cancela. Si no había
    stock (o quedaba negativo, que no debería), el costo es el de la entrada.
    """
    total_milesimas = stock_actual_milesimas + cantidad_entrada_milesimas
    if total_milesimas <= 0 or stock_actual_milesimas <= 0:
        return costo_entrada_centavos
    numerador = (
        stock_actual_milesimas * costo_actual_centavos
        + cantidad_entrada_milesimas * costo_entrada_centavos
    )
    return round_half_up(numerador, total_milesimas)
