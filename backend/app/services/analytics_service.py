"""Lógica de analítica: deriva métricas, comparativa periodo anterior y CSV.

Todo entero (centavos / bps). Eje temporal `paid_at` de ventas pagadas. El margen
se calcula sobre la base sin IVA (subtotal) menos COGS (costo snapshot × cantidad).
"""

import csv
import io
from datetime import date, datetime, time, timedelta

from sqlmodel import Session

from app.repositories import analytics_repository as repo
from app.schemas.analytics import (
    AnalyticsSummary,
    ByCashierRow,
    ByMethodRow,
    Granularidad,
    InventoryStats,
    PeakHourCell,
    SummaryComparison,
    TimeSeriesPoint,
    TopCategory,
    TopProduct,
)
from app.services.analytics_errors import InvalidDateRange
from app.services.costing import margin_bps
from app.services.money import round_half_up


def _bounds(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """desde inclusivo, hasta INCLUSIVO a nivel de día (se suma 1 día al límite)."""
    if desde > hasta:
        raise InvalidDateRange("La fecha 'desde' no puede ser posterior a 'hasta'")
    return datetime.combine(desde, time.min), datetime.combine(hasta + timedelta(days=1), time.min)


def _delta_bps(actual: int, anterior: int) -> int | None:
    if anterior == 0:
        return None
    # anterior > 0 (montos/conteos no negativos); redondeo half-up consistente.
    return round_half_up((actual - anterior) * 10000, anterior)


def _core(session: Session, desde_dt: datetime, hasta_dt: datetime) -> dict:
    ventas, subtotal, iva, n = repo.sales_totals(session, desde_dt, hasta_dt)
    cogs = round_half_up(repo.items_cogs(session, desde_dt, hasta_dt), 1000)
    margen = subtotal - cogs
    ticket = round_half_up(ventas, n) if n else 0
    return {
        "ventas": int(ventas),
        "subtotal": int(subtotal),
        "iva": int(iva),
        "cogs": cogs,
        "n": int(n),
        "ticket": ticket,
        "margen": margen,
    }


def summary(
    session: Session, desde: date, hasta: date, *, comparar: bool = True
) -> AnalyticsSummary:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    cur = _core(session, desde_dt, hasta_dt)

    comparativa = None
    if comparar:
        dias = (hasta - desde).days + 1
        prev_hasta = desde - timedelta(days=1)
        prev_desde = prev_hasta - timedelta(days=dias - 1)
        prev = _core(session, *_bounds(prev_desde, prev_hasta))
        comparativa = SummaryComparison(
            ventas_centavos=prev["ventas"],
            n_transacciones=prev["n"],
            ticket_promedio_centavos=prev["ticket"],
            margen_centavos=prev["margen"],
            delta_ventas_bps=_delta_bps(cur["ventas"], prev["ventas"]),
            delta_transacciones_bps=_delta_bps(cur["n"], prev["n"]),
            delta_ticket_bps=_delta_bps(cur["ticket"], prev["ticket"]),
            delta_margen_bps=_delta_bps(cur["margen"], prev["margen"]),
        )

    return AnalyticsSummary(
        desde=desde,
        hasta=hasta,
        ventas_centavos=cur["ventas"],
        subtotal_centavos=cur["subtotal"],
        iva_centavos=cur["iva"],
        cogs_centavos=cur["cogs"],
        n_transacciones=cur["n"],
        ticket_promedio_centavos=cur["ticket"],
        margen_centavos=cur["margen"],
        margen_bps=margin_bps(cur["subtotal"], cur["cogs"]) if cur["subtotal"] else None,
        comparativa=comparativa,
    )


def _period_start(d: date, gran: Granularidad) -> date:
    if gran == Granularidad.dia:
        return d
    if gran == Granularidad.semana:
        return d - timedelta(days=d.weekday())  # lunes (date_trunc('week'))
    if gran == Granularidad.mes:
        return d.replace(day=1)
    return d.replace(month=1, day=1)


def _next_period(d: date, gran: Granularidad) -> date:
    if gran == Granularidad.dia:
        return d + timedelta(days=1)
    if gran == Granularidad.semana:
        return d + timedelta(days=7)
    if gran == Granularidad.mes:
        return date(d.year + (d.month // 12), (d.month % 12) + 1, 1)
    return date(d.year + 1, 1, 1)


def timeseries(
    session: Session, desde: date, hasta: date, gran: Granularidad
) -> list[TimeSeriesPoint]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    filas = repo.timeseries(session, desde_dt, hasta_dt, gran.value)
    por_periodo = {
        periodo.date(): (int(ventas), int(n), int(base) - round_half_up(int(cogs), 1000))
        for periodo, ventas, n, base, cogs in filas
    }
    # Rellenar periodos sin ventas con ceros (serie continua para la gráfica).
    puntos: list[TimeSeriesPoint] = []
    p = _period_start(desde, gran)
    fin = hasta
    while p <= fin:
        ventas, n, margen = por_periodo.get(p, (0, 0, 0))
        puntos.append(
            TimeSeriesPoint(
                periodo=p, ventas_centavos=ventas, n_transacciones=n, margen_centavos=margen
            )
        )
        p = _next_period(p, gran)
    return puntos


def top_products(session: Session, desde: date, hasta: date, limit: int = 10) -> list[TopProduct]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        TopProduct(
            product_id=pid,
            nombre=nombre,
            ventas_centavos=int(ventas),
            cantidad_milesimas=int(cant),
            margen_centavos=int(base) - round_half_up(int(cogs), 1000),
        )
        for pid, nombre, ventas, cant, base, cogs in repo.top_products(
            session, desde_dt, hasta_dt, limit
        )
    ]


def top_categories(
    session: Session, desde: date, hasta: date, limit: int = 10
) -> list[TopCategory]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        TopCategory(
            categoria=cat,
            ventas_centavos=int(ventas),
            margen_centavos=int(base) - round_half_up(int(cogs), 1000),
        )
        for cat, ventas, base, cogs in repo.top_categories(session, desde_dt, hasta_dt, limit)
    ]


def by_method(session: Session, desde: date, hasta: date) -> list[ByMethodRow]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        ByMethodRow(metodo=str(metodo), ventas_centavos=int(ventas), n_transacciones=int(n))
        for metodo, ventas, n in repo.by_method(session, desde_dt, hasta_dt)
    ]


def by_cashier(session: Session, desde: date, hasta: date) -> list[ByCashierRow]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        ByCashierRow(
            user_id=uid,
            nombre=nombre,
            ventas_centavos=int(ventas),
            n_transacciones=int(n),
            ticket_promedio_centavos=round_half_up(int(ventas), int(n)) if n else 0,
        )
        for uid, nombre, ventas, n in repo.by_cashier(session, desde_dt, hasta_dt)
    ]


def peak_hours(session: Session, desde: date, hasta: date) -> list[PeakHourCell]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        PeakHourCell(
            dow=int(dow), hour=int(hour), ventas_centavos=int(ventas), n_transacciones=int(n)
        )
        for dow, hour, ventas, n in repo.peak_hours(session, desde_dt, hasta_dt)
    ]


def inventory(session: Session, desde: date, hasta: date) -> InventoryStats:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    stock_val = round_half_up(repo.stock_valorizado_num(session), 1000)
    cogs = round_half_up(repo.items_cogs(session, desde_dt, hasta_dt), 1000)
    # Rotación = COGS del rango / stock valorizado actual (en bps).
    rotacion = (cogs * 10000 // stock_val) if stock_val > 0 else None
    return InventoryStats(
        stock_valorizado_centavos=stock_val,
        cogs_periodo_centavos=cogs,
        rotacion_bps=rotacion,
        n_stock_bajo=repo.low_stock_count(session),
    )


def export_csv(session: Session, dataset: str, desde: date, hasta: date, gran: Granularidad) -> str:
    """Genera CSV server-side (una sola fuente de verdad numérica)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    if dataset == "timeseries":
        w.writerow(["periodo", "ventas_centavos", "n_transacciones", "margen_centavos"])
        for p in timeseries(session, desde, hasta, gran):
            w.writerow([p.periodo, p.ventas_centavos, p.n_transacciones, p.margen_centavos])
    elif dataset == "top-products":
        w.writerow(
            ["product_id", "nombre", "ventas_centavos", "cantidad_milesimas", "margen_centavos"]
        )
        for tp in top_products(session, desde, hasta, 100):
            w.writerow(
                [
                    tp.product_id,
                    tp.nombre,
                    tp.ventas_centavos,
                    tp.cantidad_milesimas,
                    tp.margen_centavos,
                ]
            )
    else:  # summary por defecto
        s = summary(session, desde, hasta, comparar=False)
        w.writerow(["metrica", "valor_centavos"])
        w.writerow(["ventas", s.ventas_centavos])
        w.writerow(["subtotal", s.subtotal_centavos])
        w.writerow(["iva", s.iva_centavos])
        w.writerow(["cogs", s.cogs_centavos])
        w.writerow(["margen", s.margen_centavos])
        w.writerow(["n_transacciones", s.n_transacciones])
        w.writerow(["ticket_promedio", s.ticket_promedio_centavos])
    return buf.getvalue()
