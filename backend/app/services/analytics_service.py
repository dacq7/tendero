"""Lógica de analítica: deriva métricas, comparativa periodo anterior y CSV.

Todo entero (centavos / bps). Eje temporal `paid_at` de ventas pagadas. El margen
se calcula sobre la base sin IVA (subtotal) menos COGS (costo snapshot × cantidad).
"""

import csv
import io
import statistics
from datetime import UTC, date, datetime, time, timedelta

from sqlmodel import Session

from app.repositories import analytics_repository as repo
from app.schemas.analytics import (
    AnalyticsSummary,
    ByCashierRow,
    ByMethodRow,
    CustomerSegment,
    CustomerSegments,
    Granularidad,
    GrowthPoint,
    InventoryStats,
    LowStockRow,
    PeakHourCell,
    ProfitCategory,
    ProfitMatrix,
    ProfitMatrixItem,
    ProfitProduct,
    Projection,
    ReorderRow,
    RotacionProducto,
    RotacionResumen,
    StockoutRow,
    SummaryComparison,
    SupplierConcentration,
    SupplierMargin,
    SupplierPurchases,
    TicketBucket,
    TimeSeriesPoint,
    TopCategory,
    TopCustomer,
    TopProduct,
)
from app.services.analytics_errors import InvalidDateRange
from app.services.costing import margin_bps
from app.services.money import round_half_up

CAPITAL_INMOVILIZADO_DIAS = 180  # stock con > 180 días de inventario = capital dormido


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
            nombre=nombre,
            ventas_centavos=int(ventas),
            n_transacciones=int(n),
            ticket_promedio_centavos=round_half_up(int(ventas), int(n)) if n else 0,
        )
        # `uid` se descarta: el DTO de salida no expone identificadores internos
        # (minimización; el nombre del cajero basta para la analítica admin).
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


def _dias(desde: date, hasta: date) -> int:
    return (hasta - desde).days + 1


def _margen(base: int, cogs_num: int) -> tuple[int, int, int | None]:
    """(margen_centavos, cogs_centavos, margen_bps) desde base y COGS numerador."""
    cogs = round_half_up(int(cogs_num), 1000)
    margen = int(base) - cogs
    return margen, cogs, (margin_bps(int(base), cogs) if int(base) > 0 else None)


# ── Rentabilidad ──


def profit_products(session: Session, desde: date, hasta: date) -> list[ProfitProduct]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    filas = repo.profit_by_product(session, desde_dt, hasta_dt)
    calc = [
        (pid, nombre, int(ventas), *_margen(base, cogs))
        for pid, nombre, ventas, _c, base, cogs in filas
    ]
    total_margen = sum(m for _pid, _n, _v, m, _cg, _bps in calc)
    out = [
        ProfitProduct(
            product_id=pid,
            nombre=nombre,
            ventas_centavos=ventas,
            margen_centavos=margen,
            margen_bps=bps,
            contribucion_bps=(margen * 10000 // total_margen) if total_margen > 0 else None,
        )
        for pid, nombre, ventas, margen, _cogs, bps in calc
    ]
    out.sort(key=lambda p: p.ventas_centavos, reverse=True)
    return out


def profit_categories(session: Session, desde: date, hasta: date) -> list[ProfitCategory]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    filas = repo.profit_by_category(session, desde_dt, hasta_dt)
    calc = [(cat, int(ventas), *_margen(base, cogs)) for cat, ventas, base, cogs in filas]
    total_margen = sum(m for _c, _v, m, _cg, _bps in calc)
    out = [
        ProfitCategory(
            categoria=cat,
            ventas_centavos=ventas,
            margen_centavos=margen,
            margen_bps=bps,
            contribucion_bps=(margen * 10000 // total_margen) if total_margen > 0 else None,
        )
        for cat, ventas, margen, _cogs, bps in calc
    ]
    out.sort(key=lambda c: c.ventas_centavos, reverse=True)
    return out


def profit_matrix(session: Session, desde: date, hasta: date) -> ProfitMatrix:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    filas = repo.profit_by_product(session, desde_dt, hasta_dt)
    datos = []
    for pid, nombre, ventas, cantidad, base, cogs in filas:
        _m, _c, bps = _margen(base, cogs)
        datos.append((pid, nombre, int(cantidad), int(ventas), bps if bps is not None else 0))
    if not datos:
        return ProfitMatrix(items=[], umbral_volumen_milesimas=0, umbral_margen_bps=0)
    umbral_vol = int(statistics.median([d[2] for d in datos]))
    umbral_margen = int(statistics.median([d[4] for d in datos]))
    items = []
    for pid, nombre, vol, ventas, bps in datos:
        alto_vol = vol >= umbral_vol
        alto_margen = bps >= umbral_margen
        cuadrante = (
            "estrella"
            if alto_vol and alto_margen
            else "tiron"
            if alto_vol
            else "nicho"
            if alto_margen
            else "perro"
        )
        items.append(
            ProfitMatrixItem(
                product_id=pid,
                nombre=nombre,
                volumen_milesimas=vol,
                ventas_centavos=ventas,
                margen_bps=bps,
                cuadrante=cuadrante,
            )
        )
    return ProfitMatrix(
        items=items, umbral_volumen_milesimas=umbral_vol, umbral_margen_bps=umbral_margen
    )


# ── Inventario inteligente ──


def _rotacion_centi(cogs_anual: int, stock_val: int) -> int | None:
    return (cogs_anual * 100 // stock_val) if stock_val > 0 else None


def _dias_inventario(stock_val: int, cogs_anual: int) -> int | None:
    return round_half_up(stock_val * 365, cogs_anual) if cogs_anual > 0 else None


def inventory_rotation(session: Session, desde: date, hasta: date) -> RotacionResumen:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    dias = _dias(desde, hasta)
    stock_val_total = round_half_up(repo.stock_valorizado_num(session), 1000)
    cogs_total = round_half_up(repo.items_cogs(session, desde_dt, hasta_dt), 1000)
    cogs_anual = cogs_total * 365 // dias if dias > 0 else 0

    cogs_map = repo.cogs_by_product(session, desde_dt, hasta_dt)
    por_producto: list[RotacionProducto] = []
    capital_inmovilizado = 0
    for pid, nombre, stock_mil, costo, _min in repo.active_products(session):
        stock_val_p = round_half_up(int(stock_mil) * int(costo), 1000)
        cogs_p = round_half_up(cogs_map.get(pid, 0), 1000)
        cogs_anual_p = cogs_p * 365 // dias if dias > 0 else 0
        rot = _rotacion_centi(cogs_anual_p, stock_val_p)
        dias_inv = _dias_inventario(stock_val_p, cogs_anual_p)
        # Capital dormido: stock que no rota o rota muy lento (> 180 días).
        if stock_val_p > 0 and (dias_inv is None or dias_inv > CAPITAL_INMOVILIZADO_DIAS):
            capital_inmovilizado += stock_val_p
        por_producto.append(
            RotacionProducto(
                product_id=pid,
                nombre=nombre,
                stock_valorizado_centavos=stock_val_p,
                rotacion_centi=rot,
                dias_inventario=dias_inv,
            )
        )
    por_producto.sort(key=lambda r: r.rotacion_centi or 0, reverse=True)
    return RotacionResumen(
        stock_valorizado_centavos=stock_val_total,
        cogs_periodo_centavos=cogs_total,
        cogs_anualizado_centavos=cogs_anual,
        rotacion_centi=_rotacion_centi(cogs_anual, stock_val_total),
        dias_inventario=_dias_inventario(stock_val_total, cogs_anual),
        capital_inmovilizado_centavos=capital_inmovilizado,
        por_producto=por_producto,
    )


def stockouts(session: Session, desde: date, hasta: date) -> list[StockoutRow]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        StockoutRow(product_id=pid, nombre=nombre, veces_en_cero=int(veces), ultimo=ultimo)
        for pid, nombre, veces, ultimo in repo.stockouts(session, desde_dt, hasta_dt)
    ]


def low_stock(session: Session) -> list[LowStockRow]:
    return [
        LowStockRow(
            product_id=pid,
            nombre=nombre,
            stock_milesimas=int(stock),
            stock_minimo_milesimas=int(minimo),
        )
        for pid, nombre, stock, minimo in repo.low_stock_list(session)
    ]


def reorder_suggestions(session: Session, desde: date, hasta: date) -> list[ReorderRow]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    dias = _dias(desde, hasta)
    qty_map = repo.qty_by_product(session, desde_dt, hasta_dt)
    cogs_map = repo.cogs_by_product(session, desde_dt, hasta_dt)
    out: list[ReorderRow] = []
    for pid, nombre, stock_mil, costo, minimo in repo.active_products(session):
        # Solo productos que rotan (tuvieron ventas) y están en o bajo el mínimo.
        vendido = qty_map.get(pid, 0)
        if vendido <= 0 or int(minimo) <= 0 or int(stock_mil) > int(minimo):
            continue
        # Cubrir 30 días al ritmo de venta del periodo.
        objetivo = round_half_up(vendido * 30, dias) if dias > 0 else 0
        sugerida = max(0, objetivo - int(stock_mil))
        if sugerida <= 0:
            continue
        stock_val_p = round_half_up(int(stock_mil) * int(costo), 1000)
        cogs_anual_p = round_half_up(cogs_map.get(pid, 0), 1000) * 365 // dias if dias > 0 else 0
        out.append(
            ReorderRow(
                product_id=pid,
                nombre=nombre,
                stock_milesimas=int(stock_mil),
                stock_minimo_milesimas=int(minimo),
                rotacion_centi=_rotacion_centi(cogs_anual_p, stock_val_p),
                cantidad_sugerida_milesimas=sugerida,
            )
        )
    return out


# ── Proveedores ──


def suppliers_purchases(session: Session, desde: date, hasta: date) -> list[SupplierPurchases]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        SupplierPurchases(
            supplier_id=sid,
            nombre=nombre,
            compras_centavos=round_half_up(int(compras), 1000),
            volumen_milesimas=int(vol),
            n_entradas=int(n),
        )
        for sid, nombre, compras, vol, n in repo.purchases_by_supplier(session, desde_dt, hasta_dt)
    ]


def suppliers_margin(session: Session, desde: date, hasta: date) -> list[SupplierMargin]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    out = []
    for sid, nombre, ventas, base, cogs in repo.margin_by_supplier(session, desde_dt, hasta_dt):
        margen, _cogs, bps = _margen(base, cogs)
        out.append(
            SupplierMargin(
                supplier_id=sid,
                nombre=nombre,
                ventas_centavos=int(ventas),
                margen_centavos=margen,
                margen_bps=bps,
            )
        )
    return out


def supplier_concentration(session: Session, desde: date, hasta: date) -> SupplierConcentration:
    filas = suppliers_margin(session, desde, hasta)
    reales = [f for f in filas if f.supplier_id is not None]
    total = sum(f.ventas_centavos for f in filas)
    ventas_ord = sorted((f.ventas_centavos for f in filas), reverse=True)
    top1 = (ventas_ord[0] * 10000 // total) if total > 0 and ventas_ord else None
    top3 = (sum(ventas_ord[:3]) * 10000 // total) if total > 0 and ventas_ord else None
    return SupplierConcentration(
        n_proveedores=len(reales), concentracion_top1_bps=top1, concentracion_top3_bps=top3
    )


# ── Clientes ──


def _mask_doc(doc: str) -> str:
    """Enmascara el documento (Habeas Data, Ley 1581): solo los últimos 4 dígitos.
    El documento completo NUNCA sale del backend; solo se usa como clave de
    agrupación en la query. El admin reconoce al cliente por el nombre."""
    doc = str(doc)
    return f"···{doc[-4:]}" if len(doc) > 4 else doc


def top_customers(session: Session, desde: date, hasta: date, limit: int = 10) -> list[TopCustomer]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return [
        TopCustomer(
            customer_doc=_mask_doc(doc),
            nombre=nombre,
            gasto_centavos=int(gasto),
            n_compras=int(n),
            ticket_promedio_centavos=round_half_up(int(gasto), int(n)) if n else 0,
            ultima=ultima,
        )
        for doc, nombre, gasto, n, ultima in repo.top_customers(session, desde_dt, hasta_dt, limit)
    ]


def customer_segments(session: Session, desde: date, hasta: date) -> CustomerSegments:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    ident = CustomerSegment(ventas_centavos=0, n_transacciones=0, ticket_promedio_centavos=0)
    anon = CustomerSegment(ventas_centavos=0, n_transacciones=0, ticket_promedio_centavos=0)
    for identificado, ventas, n in repo.customer_segments(session, desde_dt, hasta_dt):
        seg = CustomerSegment(
            ventas_centavos=int(ventas),
            n_transacciones=int(n),
            ticket_promedio_centavos=round_half_up(int(ventas), int(n)) if n else 0,
        )
        if identificado:
            ident = seg
        else:
            anon = seg
    return CustomerSegments(identificado=ident, anonimo=anon)


# ── Tendencias ──


def growth(session: Session, desde: date, hasta: date) -> list[GrowthPoint]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    filas = repo.timeseries(session, desde_dt, hasta_dt, "mes")
    meses = []  # (date primer-día-mes, ventas, margen)
    por_mes: dict[tuple[int, int], int] = {}
    for periodo, ventas, _n, base, cogs in filas:
        d = periodo.date().replace(day=1)
        margen = int(base) - round_half_up(int(cogs), 1000)
        meses.append((d, int(ventas), margen))
        por_mes[(d.year, d.month)] = int(ventas)
    meses.sort(key=lambda m: m[0])
    out: list[GrowthPoint] = []
    for i, (d, ventas, margen) in enumerate(meses):
        mom = _delta_bps(ventas, meses[i - 1][1]) if i > 0 else None
        anterior_yoy = por_mes.get((d.year - 1, d.month))
        yoy = _delta_bps(ventas, anterior_yoy) if anterior_yoy is not None else None
        out.append(
            GrowthPoint(
                periodo=d,
                ventas_centavos=ventas,
                margen_centavos=margen,
                mom_bps=mom,
                yoy_bps=yoy,
            )
        )
    return out


def _ticket_buckets(filas) -> list[TicketBucket]:
    return [
        TicketBucket(
            bucket=int(b),
            ventas_centavos=int(ventas),
            n_transacciones=int(n),
            ticket_promedio_centavos=round_half_up(int(ventas), int(n)) if n else 0,
        )
        for b, ventas, n in filas
    ]


def ticket_by_hour(session: Session, desde: date, hasta: date) -> list[TicketBucket]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return _ticket_buckets(repo.ticket_by_hour(session, desde_dt, hasta_dt))


def ticket_by_dow(session: Session, desde: date, hasta: date) -> list[TicketBucket]:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    return _ticket_buckets(repo.ticket_by_dow(session, desde_dt, hasta_dt))


def projection(session: Session, desde: date, hasta: date) -> Projection:
    desde_dt, hasta_dt = _bounds(desde, hasta)
    ventas_actual = int(repo.sales_totals(session, desde_dt, hasta_dt)[0])
    dias_periodo = _dias(desde, hasta)
    hoy = datetime.now(UTC).date()
    if hasta < hoy:
        # Periodo cerrado: no se proyecta.
        return Projection(
            ventas_actual_centavos=ventas_actual,
            ventas_proyectada_centavos=ventas_actual,
            dias_transcurridos=dias_periodo,
            dias_periodo=dias_periodo,
            es_estimacion=False,
        )
    transcurridos = max(1, min(dias_periodo, (hoy - desde).days + 1))
    proyectada = ventas_actual * dias_periodo // transcurridos
    return Projection(
        ventas_actual_centavos=ventas_actual,
        ventas_proyectada_centavos=proyectada,
        dias_transcurridos=transcurridos,
        dias_periodo=dias_periodo,
        es_estimacion=True,
    )


def _csv_safe(cell):
    """Neutraliza inyección de fórmulas CSV: una celda de texto que empiece con
    =,+,-,@ (o tab/CR) se interpreta como fórmula en Excel/LibreOffice. Se le
    antepone un apóstrofo para forzar texto. Los números pasan intactos."""
    if isinstance(cell, str) and cell and cell[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{cell}"
    return cell


def export_csv(session: Session, dataset: str, desde: date, hasta: date, gran: Granularidad) -> str:
    """Genera CSV server-side (una sola fuente de verdad numérica). Todo texto
    libre se sanea contra inyección de fórmulas antes de escribirse."""
    buf = io.StringIO()
    writer = csv.writer(buf)

    class _SafeWriter:
        def writerow(self, row):
            writer.writerow([_csv_safe(c) for c in row])

    w = _SafeWriter()
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
    elif dataset == "profit-products":
        w.writerow(
            [
                "product_id",
                "nombre",
                "ventas_centavos",
                "margen_centavos",
                "margen_bps",
                "contribucion_bps",
            ]
        )
        for r in profit_products(session, desde, hasta):
            w.writerow(
                [
                    r.product_id,
                    r.nombre,
                    r.ventas_centavos,
                    r.margen_centavos,
                    r.margen_bps,
                    r.contribucion_bps,
                ]
            )
    elif dataset == "profit-categories":
        w.writerow(
            ["categoria", "ventas_centavos", "margen_centavos", "margen_bps", "contribucion_bps"]
        )
        for c in profit_categories(session, desde, hasta):
            w.writerow(
                [
                    c.categoria,
                    c.ventas_centavos,
                    c.margen_centavos,
                    c.margen_bps,
                    c.contribucion_bps,
                ]
            )
    elif dataset == "inventory-rotation":
        w.writerow(
            [
                "product_id",
                "nombre",
                "stock_valorizado_centavos",
                "rotacion_centi",
                "dias_inventario",
            ]
        )
        for r in inventory_rotation(session, desde, hasta).por_producto:
            w.writerow(
                [
                    r.product_id,
                    r.nombre,
                    r.stock_valorizado_centavos,
                    r.rotacion_centi,
                    r.dias_inventario,
                ]
            )
    elif dataset == "suppliers":
        w.writerow(["supplier_id", "nombre", "ventas_centavos", "margen_centavos", "margen_bps"])
        for sm in suppliers_margin(session, desde, hasta):
            w.writerow(
                [sm.supplier_id, sm.nombre, sm.ventas_centavos, sm.margen_centavos, sm.margen_bps]
            )
    elif dataset == "customers":
        w.writerow(
            ["customer_doc", "nombre", "gasto_centavos", "n_compras", "ticket_promedio_centavos"]
        )
        for tc in top_customers(session, desde, hasta, 100):
            w.writerow(
                [
                    tc.customer_doc,
                    tc.nombre,
                    tc.gasto_centavos,
                    tc.n_compras,
                    tc.ticket_promedio_centavos,
                ]
            )
    elif dataset == "growth":
        w.writerow(["periodo", "ventas_centavos", "margen_centavos", "mom_bps", "yoy_bps"])
        for g in growth(session, desde, hasta):
            w.writerow([g.periodo, g.ventas_centavos, g.margen_centavos, g.mom_bps, g.yoy_bps])
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
