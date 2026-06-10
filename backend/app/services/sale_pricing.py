"""Cálculo de IVA y totales por línea de venta. Funciones PURAS, enteros.

El precio del producto es la BASE sin IVA (decisión confirmada): el IVA se suma
encima. total_linea = base + IVA. Redondeo half-up determinista al centavo.
Los totales de la venta se obtienen sumando líneas YA redondeadas (no se
re-redondea el total) para evitar descuadres de centavos.
"""

from typing import NamedTuple

from app.models.product import IVA_RATE_BPS, IvaRate
from app.services.money import round_half_up


class LineTotals(NamedTuple):
    base_centavos: int
    iva_bps: int
    iva_centavos: int
    total_linea_centavos: int


def line_totals(
    precio_unitario_centavos: int, iva_rate: IvaRate, cantidad_milesimas: int
) -> LineTotals:
    """Calcula base, IVA y total de una línea. Cantidad en milésimas (1000 = 1)."""
    base = round_half_up(precio_unitario_centavos * cantidad_milesimas, 1000)
    iva_bps = IVA_RATE_BPS[iva_rate]
    iva = round_half_up(base * iva_bps, 10000)
    return LineTotals(
        base_centavos=base,
        iva_bps=iva_bps,
        iva_centavos=iva,
        total_linea_centavos=base + iva,
    )


class SaleTotals(NamedTuple):
    subtotal_centavos: int
    iva_total_centavos: int
    total_centavos: int


def sale_totals(lineas: list[LineTotals]) -> SaleTotals:
    """Suma líneas ya redondeadas (sin re-redondear el total)."""
    subtotal = sum(line.base_centavos for line in lineas)
    iva_total = sum(line.iva_centavos for line in lineas)
    return SaleTotals(
        subtotal_centavos=subtotal,
        iva_total_centavos=iva_total,
        total_centavos=subtotal + iva_total,
    )
