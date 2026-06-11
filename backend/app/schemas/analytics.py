"""DTOs de analítica. Dinero en centavos, márgenes en bps (enteros)."""

from datetime import date, datetime
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
    # Sin `user_id`: el DTO de salida no expone identificadores internos (Fase 6 B.1).
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


# ───────────────────── Fase 5.2: analítica profesional ─────────────────────


class ProfitProduct(BaseModel):
    product_id: int
    nombre: str
    ventas_centavos: int
    margen_centavos: int
    margen_bps: int | None
    contribucion_bps: int | None  # aporte a la utilidad bruta total


class ProfitCategory(BaseModel):
    categoria: str
    ventas_centavos: int
    margen_centavos: int
    margen_bps: int | None
    contribucion_bps: int | None


class ProfitMatrixItem(BaseModel):
    product_id: int
    nombre: str
    volumen_milesimas: int
    ventas_centavos: int
    margen_bps: int | None
    cuadrante: str  # estrella | tiron | nicho | perro


class ProfitMatrix(BaseModel):
    items: list[ProfitMatrixItem]
    umbral_volumen_milesimas: int
    umbral_margen_bps: int


class RotacionProducto(BaseModel):
    product_id: int
    nombre: str
    stock_valorizado_centavos: int
    rotacion_centi: int | None  # veces/año ×100 (350 = 3.50 veces/año)
    dias_inventario: int | None


class RotacionResumen(BaseModel):
    stock_valorizado_centavos: int
    cogs_periodo_centavos: int
    cogs_anualizado_centavos: int
    rotacion_centi: int | None  # veces/año ×100
    dias_inventario: int | None
    capital_inmovilizado_centavos: int  # stock de productos que rotan lento (>180 días)
    por_producto: list[RotacionProducto]


class StockoutRow(BaseModel):
    product_id: int
    nombre: str
    veces_en_cero: int
    ultimo: datetime


class LowStockRow(BaseModel):
    product_id: int
    nombre: str
    stock_milesimas: int
    stock_minimo_milesimas: int


class ReorderRow(BaseModel):
    product_id: int
    nombre: str
    stock_milesimas: int
    stock_minimo_milesimas: int
    rotacion_centi: int | None
    cantidad_sugerida_milesimas: int


class SupplierPurchases(BaseModel):
    supplier_id: int
    nombre: str
    compras_centavos: int
    volumen_milesimas: int
    n_entradas: int


class SupplierMargin(BaseModel):
    supplier_id: int | None
    nombre: str
    ventas_centavos: int
    margen_centavos: int
    margen_bps: int | None


class SupplierConcentration(BaseModel):
    n_proveedores: int
    concentracion_top1_bps: int | None
    concentracion_top3_bps: int | None


class TopCustomer(BaseModel):
    customer_doc: str
    nombre: str | None
    gasto_centavos: int
    n_compras: int
    ticket_promedio_centavos: int
    ultima: datetime | None


class CustomerSegment(BaseModel):
    ventas_centavos: int
    n_transacciones: int
    ticket_promedio_centavos: int


class CustomerSegments(BaseModel):
    identificado: CustomerSegment
    anonimo: CustomerSegment


class GrowthPoint(BaseModel):
    periodo: date
    ventas_centavos: int
    margen_centavos: int
    mom_bps: int | None
    yoy_bps: int | None


class TicketBucket(BaseModel):
    bucket: int  # hora (0-23) o día de semana (0-6)
    ventas_centavos: int
    n_transacciones: int
    ticket_promedio_centavos: int


class Projection(BaseModel):
    ventas_actual_centavos: int
    ventas_proyectada_centavos: int
    dias_transcurridos: int
    dias_periodo: int
    es_estimacion: bool
