"""Lógica de productos. No conoce HTTP: lanza errores de dominio.

Regla de oro: este service NUNCA modifica el stock. El stock cambia solo a
través de inventory_service.apply_movement (kardex auditable).
"""

from sqlmodel import Session

from app.models.product import Product
from app.repositories import product_repository, supplier_repository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.inventory_errors import (
    DuplicateBarcode,
    DuplicateSku,
    ProductNotFound,
    SupplierNotFound,
)


def get(session: Session, product_id: int) -> Product:
    product = product_repository.get(session, product_id)
    if product is None:
        raise ProductNotFound(f"Producto {product_id} no encontrado")
    return product


def get_locked(session: Session, product_id: int) -> Product:
    """Como get(), pero bloquea la fila (FOR UPDATE) para mutar stock sin carreras."""
    product = product_repository.get_for_update(session, product_id)
    if product is None:
        raise ProductNotFound(f"Producto {product_id} no encontrado")
    return product


def get_by_barcode(session: Session, codigo_barras: str) -> Product:
    product = product_repository.get_by_barcode(session, codigo_barras)
    if product is None:
        raise ProductNotFound(f"No hay producto con código de barras {codigo_barras}")
    return product


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
    return product_repository.search(
        session,
        q=q,
        categoria=categoria,
        solo_activos=solo_activos,
        stock_bajo=stock_bajo,
        offset=offset,
        limit=limit,
    )


def _ensure_supplier_exists(session: Session, supplier_id: int | None) -> None:
    if supplier_id is not None and supplier_repository.get(session, supplier_id) is None:
        raise SupplierNotFound(f"Proveedor {supplier_id} no encontrado")


def _ensure_sku_libre(session: Session, sku: str, *, excluir_id: int | None = None) -> None:
    existente = product_repository.get_by_sku(session, sku)
    if existente is not None and existente.id != excluir_id:
        raise DuplicateSku(f"Ya existe un producto con SKU {sku}")


def _ensure_barcode_libre(
    session: Session, codigo_barras: str | None, *, excluir_id: int | None = None
) -> None:
    if codigo_barras is None:
        return
    existente = product_repository.get_by_barcode(session, codigo_barras)
    if existente is not None and existente.id != excluir_id:
        raise DuplicateBarcode(f"Ya existe un producto con código de barras {codigo_barras}")


def create(session: Session, data: ProductCreate) -> Product:
    _ensure_sku_libre(session, data.sku)
    _ensure_barcode_libre(session, data.codigo_barras)
    _ensure_supplier_exists(session, data.supplier_id)
    # stock arranca en 0: se carga con una entrada de mercancía (kardex).
    product = Product(
        nombre=data.nombre,
        sku=data.sku,
        codigo_barras=data.codigo_barras,
        categoria=data.categoria,
        supplier_id=data.supplier_id,
        precio_costo_centavos=data.precio_costo_centavos,
        precio_venta_centavos=data.precio_venta_centavos,
        iva=data.iva,
        unidad=data.unidad,
        stock_minimo_milesimas=data.stock_minimo_milesimas,
    )
    product_repository.add(session, product)
    session.commit()
    session.refresh(product)
    return product


def update(session: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get(session, product_id)
    cambios = data.model_dump(exclude_unset=True)
    if "sku" in cambios and cambios["sku"] is not None:
        _ensure_sku_libre(session, cambios["sku"], excluir_id=product_id)
    if "codigo_barras" in cambios:
        _ensure_barcode_libre(session, cambios["codigo_barras"], excluir_id=product_id)
    if "supplier_id" in cambios:
        _ensure_supplier_exists(session, cambios["supplier_id"])
    for field, value in cambios.items():
        setattr(product, field, value)
    product_repository.add(session, product)
    session.commit()
    session.refresh(product)
    return product


def deactivate(session: Session, product_id: int) -> None:
    """Baja lógica: el producto conserva su kardex."""
    product = get(session, product_id)
    product.activo = False
    product_repository.add(session, product)
    session.commit()
