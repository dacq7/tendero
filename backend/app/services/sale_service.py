"""Venta atómica: descuenta stock (reutiliza apply_movement), congela snapshots,
calcula totales y emite la factura interna — TODO en una transacción.

Si cualquier paso falla (p. ej. stock insuficiente), la excepción aborta el
commit y SQLAlchemy revierte: no se descuenta stock, no se crea factura y el
número de factura NO se consume.
"""

from datetime import UTC, datetime

from sqlmodel import Session

from app.models.inventory_movement import MovementType
from app.models.invoice import Invoice
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.user import User, UserRole
from app.repositories import (
    cash_repository,
    invoice_repository,
    invoice_sequence_repository,
    sale_repository,
)
from app.schemas.sale import SaleCreate
from app.services import inventory_service, product_service, sale_pricing
from app.services.sales_errors import (
    EmptySale,
    InvoiceNotFound,
    NoCashSessionOpen,
    SaleNotFound,
)

_SERIE = "POS"


def create_sale(session: Session, data: SaleCreate, *, user_id: int) -> Sale:
    if not data.lineas:
        raise EmptySale("La venta no tiene líneas")

    cash = cash_repository.get_open_for_update(session)
    if cash is None:
        raise NoCashSessionOpen("No hay caja abierta — ábrela para empezar a vender")

    # 1) Descontar stock (FOR UPDATE por producto) y congelar pricing por línea.
    calculadas: list[tuple] = []
    for linea in data.lineas:
        product = product_service.get_locked(session, linea.product_id)
        inventory_service.apply_movement(
            session,
            product,
            tipo=MovementType.salida,
            cantidad_milesimas=linea.cantidad_milesimas,
            motivo="Venta",
            user_id=user_id,
        )
        lt = sale_pricing.line_totals(
            product.precio_venta_centavos, product.iva, linea.cantidad_milesimas
        )
        calculadas.append((product, linea, lt))

    totals = sale_pricing.sale_totals([lt for _, _, lt in calculadas])

    # 2) Crear la venta (con totales coherentes con el CHECK total = subtotal + iva).
    sale = Sale(
        cash_session_id=cash.id,
        user_id=user_id,
        customer_doc=data.customer_doc,
        customer_nombre=data.customer_nombre,
        subtotal_centavos=totals.subtotal_centavos,
        iva_total_centavos=totals.iva_total_centavos,
        total_centavos=totals.total_centavos,
        status=SaleStatus.pendiente,
    )
    sale_repository.add(session, sale)

    # 3) Líneas con snapshot congelado.
    for product, linea, lt in calculadas:
        sale_repository.add_item(
            session,
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                nombre_snapshot=product.nombre,
                sku_snapshot=product.sku,
                cantidad_milesimas=linea.cantidad_milesimas,
                precio_unitario_centavos=product.precio_venta_centavos,
                iva_rate_snapshot=product.iva,
                iva_bps_snapshot=lt.iva_bps,
                base_centavos=lt.base_centavos,
                iva_centavos=lt.iva_centavos,
                total_linea_centavos=lt.total_linea_centavos,
            ),
        )

    # 4) Factura interna con número secuencial (sin huecos ni duplicados).
    numero = invoice_sequence_repository.next_numero(session, _SERIE)
    invoice = Invoice(
        sale_id=sale.id,
        serie=_SERIE,
        numero=numero,
        numero_completo=f"{_SERIE}-{numero:06d}",
        subtotal_centavos=totals.subtotal_centavos,
        iva_total_centavos=totals.iva_total_centavos,
        total_centavos=totals.total_centavos,
        metodo_pago=data.metodo_pago,
    )
    invoice_repository.add(session, invoice)

    # 5) Cobro local (sin Wompi en Fase 2): marcar pagada.
    sale.status = SaleStatus.pagada
    sale.metodo_pago = data.metodo_pago
    sale.paid_at = datetime.now(UTC)
    sale_repository.add(session, sale)

    session.commit()
    session.refresh(sale)
    return sale


def get_sale(session: Session, sale_id: int) -> Sale:
    sale = sale_repository.get(session, sale_id)
    if sale is None:
        raise SaleNotFound(f"Venta {sale_id} no encontrada")
    return sale


def list_sales(
    session: Session,
    *,
    actor: User,
    cash_session_id: int | None = None,
    status: SaleStatus | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Sale]:
    # El cajero ve solo sus ventas; el admin, todas.
    user_id = None if actor.role == UserRole.admin else actor.id
    return sale_repository.list_all(
        session,
        cash_session_id=cash_session_id,
        user_id=user_id,
        status=status,
        offset=offset,
        limit=limit,
    )


def sale_detail(session: Session, sale_id: int) -> tuple[Sale, list[SaleItem], Invoice]:
    sale = get_sale(session, sale_id)
    items = sale_repository.items_for_sale(session, sale_id)
    invoice = invoice_repository.get_by_sale(session, sale_id)
    if invoice is None:
        raise InvoiceNotFound(f"La venta {sale_id} no tiene factura")
    return sale, items, invoice
