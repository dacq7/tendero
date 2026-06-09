"""Acceso a datos de productos. Solo queries; sin lógica de negocio.

No hace commit: la frontera transaccional la controla el service.
"""

from sqlmodel import Session, col, or_, select

from app.models.product import Product


def get(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)


def get_for_update(session: Session, product_id: int) -> Product | None:
    """Carga el producto con bloqueo de fila (SELECT ... FOR UPDATE).

    Necesario al mutar stock: serializa movimientos concurrentes sobre el mismo
    producto y evita carreras que dejarían el stock inconsistente.
    """
    stmt = select(Product).where(Product.id == product_id).with_for_update()
    return session.exec(stmt).first()


def get_by_sku(session: Session, sku: str) -> Product | None:
    return session.exec(select(Product).where(Product.sku == sku)).first()


def get_by_barcode(session: Session, codigo_barras: str) -> Product | None:
    return session.exec(select(Product).where(Product.codigo_barras == codigo_barras)).first()


def search(
    session: Session,
    *,
    q: str | None = None,
    categoria: str | None = None,
    solo_activos: bool = True,
    stock_bajo: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> list[Product]:
    stmt = select(Product)
    if solo_activos:
        stmt = stmt.where(Product.activo)
    if q:
        patron = f"%{q}%"
        stmt = stmt.where(
            or_(
                col(Product.nombre).ilike(patron),
                col(Product.sku).ilike(patron),
                col(Product.codigo_barras).ilike(patron),
            )
        )
    if categoria:
        stmt = stmt.where(Product.categoria == categoria)
    if stock_bajo:
        # Un mínimo de 0 significa "sin control de mínimo": no genera alerta.
        stmt = stmt.where(Product.stock_minimo_milesimas > 0).where(
            Product.stock_milesimas <= Product.stock_minimo_milesimas
        )
    stmt = stmt.order_by(Product.nombre).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


def low_stock(session: Session) -> list[Product]:
    """Productos activos con mínimo configurado (>0) y stock en o bajo el mínimo."""
    stmt = (
        select(Product)
        .where(Product.activo)
        .where(Product.stock_minimo_milesimas > 0)
        .where(Product.stock_milesimas <= Product.stock_minimo_milesimas)
        .order_by(Product.nombre)
    )
    return list(session.exec(stmt).all())


def add(session: Session, product: Product) -> Product:
    """Inserta o actualiza (flush para asignar id y disparar constraints)."""
    session.add(product)
    session.flush()
    return product
