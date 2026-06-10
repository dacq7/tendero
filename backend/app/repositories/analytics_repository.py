"""Agregaciones de analítica. SOLO lecturas (SELECT con GROUP BY). Sin commit.

Eje temporal: `paid_at` de ventas con `status='pagada'` (ingresos reales). Los
montos son enteros (centavos); 'ventas' = total con IVA; el margen se deriva en el
service desde base (sin IVA) menos COGS (costo snapshot × cantidad / 1000).
"""

from datetime import datetime

from sqlalchemy import BigInteger, cast, func
from sqlmodel import Session, select

from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier
from app.models.user import User


def _purchase_expr():
    """costo_unitario × cantidad de una entrada (cast BigInteger anti-overflow)."""
    return (
        cast(InventoryMovement.costo_unitario_centavos, BigInteger)
        * InventoryMovement.cantidad_milesimas
    )

# Unidad de date_trunc por granularidad.
TRUNC = {"dia": "day", "semana": "week", "mes": "month", "ano": "year"}


def _cogs_expr():
    """costo × cantidad por fila, casteado a BigInteger antes de multiplicar para
    evitar overflow de int32 (costos altos × cantidades grandes)."""
    return cast(SaleItem.costo_unitario_snapshot_centavos, BigInteger) * SaleItem.cantidad_milesimas


def _stock_val_expr():
    return cast(Product.stock_milesimas, BigInteger) * Product.precio_costo_centavos


def _ventas_pagadas(desde: datetime, hasta: datetime):
    return (Sale.status == SaleStatus.pagada) & (Sale.paid_at >= desde) & (Sale.paid_at < hasta)


def sales_totals(session: Session, desde: datetime, hasta: datetime):
    """(ventas_total, subtotal, iva, n_transacciones) de ventas pagadas."""
    stmt = select(
        func.coalesce(func.sum(Sale.total_centavos), 0),
        func.coalesce(func.sum(Sale.subtotal_centavos), 0),
        func.coalesce(func.sum(Sale.iva_total_centavos), 0),
        func.count(Sale.id),
    ).where(_ventas_pagadas(desde, hasta))
    return session.exec(stmt).one()


def items_cogs(session: Session, desde: datetime, hasta: datetime) -> int:
    """COGS numerador = Σ(costo_snapshot × cantidad_milesimas) (dividir por 1000 fuera)."""
    stmt = (
        select(
            func.coalesce(
                func.sum(_cogs_expr()),
                0,
            )
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(_ventas_pagadas(desde, hasta))
    )
    return int(session.exec(stmt).one())


def timeseries(session: Session, desde: datetime, hasta: datetime, granularidad: str):
    """Por periodo: (periodo, ventas, n, base, cogs_num)."""
    periodo = func.date_trunc(TRUNC[granularidad], Sale.paid_at).label("periodo")
    stmt = (
        select(
            periodo,
            func.coalesce(func.sum(SaleItem.total_linea_centavos), 0),
            func.count(func.distinct(Sale.id)),
            func.coalesce(func.sum(SaleItem.base_centavos), 0),
            func.coalesce(
                func.sum(_cogs_expr()),
                0,
            ),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(periodo)
        .order_by(periodo)
    )
    return session.exec(stmt).all()


def top_products(session: Session, desde: datetime, hasta: datetime, limit: int):
    stmt = (
        select(
            SaleItem.product_id,
            SaleItem.nombre_snapshot,
            func.sum(SaleItem.total_linea_centavos),
            func.sum(SaleItem.cantidad_milesimas),
            func.sum(SaleItem.base_centavos),
            func.sum(_cogs_expr()),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(SaleItem.product_id, SaleItem.nombre_snapshot)
        .order_by(func.sum(SaleItem.total_linea_centavos).desc())
        .limit(limit)
    )
    return session.exec(stmt).all()


def top_categories(session: Session, desde: datetime, hasta: datetime, limit: int):
    cat = func.coalesce(Product.categoria, "Sin categoría").label("categoria")
    stmt = (
        select(
            cat,
            func.sum(SaleItem.total_linea_centavos),
            func.sum(SaleItem.base_centavos),
            func.sum(_cogs_expr()),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(cat)
        .order_by(func.sum(SaleItem.total_linea_centavos).desc())
        .limit(limit)
    )
    return session.exec(stmt).all()


def by_method(session: Session, desde: datetime, hasta: datetime):
    stmt = (
        select(Sale.metodo_pago, func.sum(Sale.total_centavos), func.count(Sale.id))
        .where(_ventas_pagadas(desde, hasta))
        .group_by(Sale.metodo_pago)
        .order_by(func.sum(Sale.total_centavos).desc())
    )
    return session.exec(stmt).all()


def by_cashier(session: Session, desde: datetime, hasta: datetime):
    stmt = (
        select(
            Sale.user_id,
            func.coalesce(User.full_name, "—"),
            func.sum(Sale.total_centavos),
            func.count(Sale.id),
        )
        .select_from(Sale)
        .join(User, User.id == Sale.user_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(Sale.user_id, User.full_name)
        .order_by(func.sum(Sale.total_centavos).desc())
    )
    return session.exec(stmt).all()


def peak_hours(session: Session, desde: datetime, hasta: datetime):
    dow = func.extract("dow", Sale.paid_at).label("dow")
    hour = func.extract("hour", Sale.paid_at).label("hour")
    stmt = (
        select(dow, hour, func.sum(Sale.total_centavos), func.count(Sale.id))
        .where(_ventas_pagadas(desde, hasta))
        .group_by(dow, hour)
    )
    return session.exec(stmt).all()


def stock_valorizado_num(session: Session) -> int:
    """Σ(stock_milesimas × precio_costo_centavos) sobre activos (÷1000 fuera)."""
    stmt = select(func.coalesce(func.sum(_stock_val_expr()), 0)).where(Product.activo)
    return int(session.exec(stmt).one())


def low_stock_count(session: Session) -> int:
    stmt = (
        select(func.count(Product.id))
        .where(Product.activo)
        .where(Product.stock_minimo_milesimas > 0)
        .where(Product.stock_milesimas <= Product.stock_minimo_milesimas)
    )
    return int(session.exec(stmt).one())


# ───────────────────── Fase 5.2: analítica profesional ─────────────────────


def profit_by_product(session: Session, desde: datetime, hasta: datetime):
    """Por producto (TODOS): (product_id, nombre, ventas, cantidad, base, cogs_num)."""
    stmt = (
        select(
            SaleItem.product_id,
            SaleItem.nombre_snapshot,
            func.sum(SaleItem.total_linea_centavos),
            func.sum(SaleItem.cantidad_milesimas),
            func.sum(SaleItem.base_centavos),
            func.sum(_cogs_expr()),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(SaleItem.product_id, SaleItem.nombre_snapshot)
    )
    return session.exec(stmt).all()


def profit_by_category(session: Session, desde: datetime, hasta: datetime):
    """Por categoría (TODAS): (categoria, ventas, base, cogs_num)."""
    cat = func.coalesce(Product.categoria, "Sin categoría").label("categoria")
    stmt = (
        select(
            cat,
            func.sum(SaleItem.total_linea_centavos),
            func.sum(SaleItem.base_centavos),
            func.sum(_cogs_expr()),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(cat)
    )
    return session.exec(stmt).all()


def cogs_by_product(session: Session, desde: datetime, hasta: datetime) -> dict[int, int]:
    """{product_id: cogs_num} de ventas pagadas (para rotación por producto)."""
    stmt = (
        select(SaleItem.product_id, func.sum(_cogs_expr()))
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(SaleItem.product_id)
    )
    return {pid: int(cogs) for pid, cogs in session.exec(stmt).all()}


def qty_by_product(session: Session, desde: datetime, hasta: datetime) -> dict[int, int]:
    """{product_id: unidades_vendidas_milesimas} (para consumo diario / recompra)."""
    stmt = (
        select(SaleItem.product_id, func.sum(SaleItem.cantidad_milesimas))
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(SaleItem.product_id)
    )
    return {pid: int(q) for pid, q in session.exec(stmt).all()}


def active_products(session: Session):
    """Productos activos (id, nombre, stock, costo, mínimo) para inventario."""
    stmt = select(
        Product.id,
        Product.nombre,
        Product.stock_milesimas,
        Product.precio_costo_centavos,
        Product.stock_minimo_milesimas,
    ).where(Product.activo)
    return session.exec(stmt).all()


def stockouts(session: Session, desde: datetime, hasta: datetime):
    """Productos que tocaron 0 en el kardex: (product_id, nombre, veces, ultimo)."""
    stmt = (
        select(
            InventoryMovement.product_id,
            Product.nombre,
            func.count(),
            func.max(InventoryMovement.created_at),
        )
        .select_from(InventoryMovement)
        .join(Product, Product.id == InventoryMovement.product_id)
        .where(InventoryMovement.stock_resultante_milesimas == 0)
        .where(InventoryMovement.created_at >= desde)
        .where(InventoryMovement.created_at < hasta)
        .group_by(InventoryMovement.product_id, Product.nombre)
        .order_by(func.count().desc())
    )
    return session.exec(stmt).all()


def low_stock_list(session: Session):
    """Productos activos en o bajo el mínimo (mínimo > 0)."""
    stmt = (
        select(
            Product.id,
            Product.nombre,
            Product.stock_milesimas,
            Product.stock_minimo_milesimas,
        )
        .where(Product.activo)
        .where(Product.stock_minimo_milesimas > 0)
        .where(Product.stock_milesimas <= Product.stock_minimo_milesimas)
        .order_by(Product.nombre)
    )
    return session.exec(stmt).all()


def purchases_by_supplier(session: Session, desde: datetime, hasta: datetime):
    """Compras por proveedor desde entradas: (supplier_id, nombre, compras_num, vol, n)."""
    stmt = (
        select(
            Supplier.id,
            Supplier.nombre,
            func.sum(_purchase_expr()),
            func.sum(InventoryMovement.cantidad_milesimas),
            func.count(),
        )
        .select_from(InventoryMovement)
        .join(Product, Product.id == InventoryMovement.product_id)
        .join(Supplier, Supplier.id == Product.supplier_id)
        .where(InventoryMovement.tipo == MovementType.entrada)
        .where(InventoryMovement.costo_unitario_centavos.is_not(None))
        .where(InventoryMovement.created_at >= desde)
        .where(InventoryMovement.created_at < hasta)
        .group_by(Supplier.id, Supplier.nombre)
        .order_by(func.sum(_purchase_expr()).desc())
    )
    return session.exec(stmt).all()


def margin_by_supplier(session: Session, desde: datetime, hasta: datetime):
    """Margen aportado por proveedor: (supplier_id, nombre, ventas, base, cogs_num).
    Incluye 'Sin proveedor' (LEFT JOIN) para que los totales cuadren."""
    nombre = func.coalesce(Supplier.nombre, "Sin proveedor").label("nombre")
    stmt = (
        select(
            Product.supplier_id,
            nombre,
            func.sum(SaleItem.total_linea_centavos),
            func.sum(SaleItem.base_centavos),
            func.sum(_cogs_expr()),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .join(Supplier, Supplier.id == Product.supplier_id, isouter=True)
        .where(_ventas_pagadas(desde, hasta))
        .group_by(Product.supplier_id, nombre)
        .order_by(func.sum(SaleItem.total_linea_centavos).desc())
    )
    return session.exec(stmt).all()


def top_customers(session: Session, desde: datetime, hasta: datetime, limit: int):
    """Mejores clientes por gasto (agrupa por customer_doc, no nulo)."""
    stmt = (
        select(
            Sale.customer_doc,
            func.max(Sale.customer_nombre),
            func.sum(Sale.total_centavos),
            func.count(),
            func.max(Sale.paid_at),
        )
        .where(_ventas_pagadas(desde, hasta))
        .where(Sale.customer_doc.is_not(None))
        .group_by(Sale.customer_doc)
        .order_by(func.sum(Sale.total_centavos).desc())
        .limit(limit)
    )
    return session.exec(stmt).all()


def customer_segments(session: Session, desde: datetime, hasta: datetime):
    """(identificado: bool, ventas, n) — recurrente/identificado vs anónimo."""
    identificado = Sale.customer_doc.is_not(None).label("identificado")
    stmt = (
        select(identificado, func.sum(Sale.total_centavos), func.count())
        .where(_ventas_pagadas(desde, hasta))
        .group_by(identificado)
    )
    return session.exec(stmt).all()


def ticket_by_hour(session: Session, desde: datetime, hasta: datetime):
    hour = func.extract("hour", Sale.paid_at).label("hour")
    stmt = (
        select(hour, func.sum(Sale.total_centavos), func.count())
        .where(_ventas_pagadas(desde, hasta))
        .group_by(hour)
        .order_by(hour)
    )
    return session.exec(stmt).all()


def ticket_by_dow(session: Session, desde: datetime, hasta: datetime):
    dow = func.extract("dow", Sale.paid_at).label("dow")
    stmt = (
        select(dow, func.sum(Sale.total_centavos), func.count())
        .where(_ventas_pagadas(desde, hasta))
        .group_by(dow)
        .order_by(dow)
    )
    return session.exec(stmt).all()


# Reexport para el service.
PAYMENT_METHODS = [m.value for m in PaymentMethod]
