"""DTOs de analítica. Dinero en centavos, márgenes en bps (enteros)."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class Granularidad(StrEnum):
    dia = "dia"
    semana = "semana"
    mes = "mes"
    ano = "ano"


class SummaryComparison(BaseModel):
    """Periodo anterior del mismo tamaño + deltas en bps (None si no hay base)."""

    ventas_centavos: int
    n_transacciones: int
    ticket_promedio_centavos: int
    margen_centavos: int
    delta_ventas_bps: int | None
    delta_transacciones_bps: int | None
    delta_ticket_bps: int | None
    delta_margen_bps: int | None


class AnalyticsSummary(BaseModel):
    desde: date
    hasta: date
    ventas_centavos: int
    subtotal_centavos: int
    iva_centavos: int
    cogs_centavos: int
    n_transacciones: int
    ticket_promedio_centavos: int
    margen_centavos: int
    margen_bps: int | None
    comparativa: SummaryComparison | None


class TimeSeriesPoint(BaseModel):
    periodo: date
    ventas_centavos: int
    n_transacciones: int
    margen_centavos: int


class TopProduct(BaseModel):
    product_id: int
    nombre: str
    ventas_centavos: int
    cantidad_milesimas: int
    margen_centavos: int


class TopCategory(BaseModel):
    categoria: str
    ventas_centavos: int
    margen_centavos: int


class ByMethodRow(BaseModel):
    metodo: str
    ventas_centavos: int
    n_transacciones: int


class ByCashierRow(BaseModel):
    user_id: int
    nombre: str
    ventas_centavos: int
    n_transacciones: int
    ticket_promedio_centavos: int


class PeakHourCell(BaseModel):
    dow: int  # 0=domingo (date_part) .. 6=sábado
    hour: int
    ventas_centavos: int
    n_transacciones: int


class InventoryStats(BaseModel):
    stock_valorizado_centavos: int
    cogs_periodo_centavos: int
    rotacion_bps: int | None  # COGS del rango / stock valorizado, en bps
    n_stock_bajo: int
