"""Corazón del inventario: stock y costeo. No conoce HTTP.

INVARIANTE: `apply_movement` es el ÚNICO lugar que muta `product.stock_milesimas`.
Todo cambio de stock pasa por aquí y deja huella en el kardex (auditable).
`apply_movement` NO hace commit: la frontera transaccional la fija quien lo llama,
para que la entrada de mercancía multilínea sea atómica.
"""

from datetime import datetime

from sqlmodel import Session

from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.repositories import movement_repository, product_repository, supplier_repository
from app.schemas.inventory import GoodsEntryCreate, MovementCreate
from app.services import costing, product_service
from app.services.inventory_errors import (
    InsufficientStock,
    InvalidCost,
    InvalidQuantity,
    SupplierNotFound,
)

_DESCUENTAN = (MovementType.salida, MovementType.merma)


def apply_movement(
    session: Session,
    product: Product,
    *,
    tipo: MovementType,
    cantidad_milesimas: int,
    costo_unitario_centavos: int | None = None,
    motivo: str | None = None,
    user_id: int | None = None,
) -> InventoryMovement:
    """Aplica un movimiento al stock del producto y lo registra en el kardex.

    Devuelve el movimiento creado (sin commit). Lanza errores de dominio si la
    operación es inválida (cantidad, costo o stock insuficiente).
    """
    if cantidad_milesimas <= 0:
        raise InvalidQuantity("La cantidad debe ser mayor que cero")

    stock_actual = product.stock_milesimas

    if tipo == MovementType.entrada:
        if costo_unitario_centavos is None:
            raise InvalidCost("Una entrada requiere costo unitario")
        magnitud = cantidad_milesimas
        nuevo_stock = stock_actual + cantidad_milesimas
        # Costo promedio ponderado y costo de referencia del producto.
        product.precio_costo_centavos = costing.weighted_average_cost(
            stock_actual,
            product.precio_costo_centavos,
            cantidad_milesimas,
            costo_unitario_centavos,
        )
    elif tipo == MovementType.reverso_venta:
        # Devuelve lo reservado por una venta rechazada. Suma SIN recostear: no
        # es una compra, así que NO toca precio_costo (a diferencia de entrada).
        magnitud = cantidad_milesimas
        nuevo_stock = stock_actual + cantidad_milesimas
    elif tipo in _DESCUENTAN:
        magnitud = cantidad_milesimas
        nuevo_stock = stock_actual - cantidad_milesimas
        if nuevo_stock < 0:
            raise InsufficientStock(
                f"Stock insuficiente: hay {stock_actual}, se intentó descontar "
                f"{cantidad_milesimas} (milésimas)"
            )
    else:  # ajuste: cantidad es el stock objetivo
        objetivo = cantidad_milesimas
        delta = objetivo - stock_actual
        if delta == 0:
            raise InvalidQuantity("El ajuste no cambia el stock")
        magnitud = abs(delta)
        nuevo_stock = objetivo

    product.stock_milesimas = nuevo_stock
    product_repository.add(session, product)

    movement = InventoryMovement(
        product_id=product.id,
        tipo=tipo,
        cantidad_milesimas=magnitud,
        costo_unitario_centavos=costo_unitario_centavos,
        stock_resultante_milesimas=nuevo_stock,
        motivo=motivo,
        user_id=user_id,
    )
    movement_repository.add(session, movement)
    return movement


def register_movement(
    session: Session, data: MovementCreate, *, user_id: int | None
) -> InventoryMovement:
    """Registra un movimiento individual (carga producto, aplica y commitea)."""
    product = product_service.get_locked(session, data.product_id)
    movement = apply_movement(
        session,
        product,
        tipo=data.tipo,
        cantidad_milesimas=data.cantidad_milesimas,
        costo_unitario_centavos=data.costo_unitario_centavos,
        motivo=data.motivo,
        user_id=user_id,
    )
    session.commit()
    session.refresh(movement)
    return movement


def register_goods_entry(
    session: Session, data: GoodsEntryCreate, *, user_id: int | None
) -> list[InventoryMovement]:
    """Entrada de mercancía multilínea ATÓMICA: si una línea falla, no se aplica
    ninguna (un solo commit al final; cualquier excepción deja la transacción sin
    confirmar y SQLAlchemy hace rollback al cerrar la sesión)."""
    if data.supplier_id is not None:
        if supplier_repository.get(session, data.supplier_id) is None:
            raise SupplierNotFound(f"Proveedor {data.supplier_id} no encontrado")

    movimientos: list[InventoryMovement] = []
    for linea in data.lineas:
        product = product_service.get_locked(session, linea.product_id)
        movimiento = apply_movement(
            session,
            product,
            tipo=MovementType.entrada,
            cantidad_milesimas=linea.cantidad_milesimas,
            costo_unitario_centavos=linea.costo_unitario_centavos,
            motivo=data.motivo,
            user_id=user_id,
        )
        movimientos.append(movimiento)

    session.commit()
    for m in movimientos:
        session.refresh(m)
    return movimientos


def low_stock_alerts(session: Session) -> list[Product]:
    return product_repository.low_stock(session)


def product_kardex(session: Session, product_id: int) -> list[InventoryMovement]:
    """Kardex de un producto (valida que exista; 404 si no)."""
    product_service.get(session, product_id)
    return movement_repository.list_for_product(session, product_id)


def list_movements(
    session: Session,
    *,
    product_id: int | None = None,
    tipo: MovementType | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[InventoryMovement]:
    return movement_repository.list_all(
        session,
        product_id=product_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
        offset=offset,
        limit=limit,
    )
