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
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
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
    NoCashSessionOpen,
    SaleNotFound,
)

_SERIE = "POS"

# Métodos que se cobran por Wompi (asíncrono). El resto es cobro local (síncrono).
WOMPI_METHODS = frozenset({PaymentMethod.tarjeta, PaymentMethod.pse, PaymentMethod.nequi})


def emit_invoice(
    session: Session, sale: Sale, *, metodo_pago: PaymentMethod, wompi_transaction_id=None
) -> Invoice:
    """Numera y crea la factura interna de una venta (sin huecos ni duplicados).

    Reutilizada por el cobro local (en create_sale) y por el webhook approved.
    """
    numero = invoice_sequence_repository.next_numero(session, _SERIE)
    invoice = Invoice(
        sale_id=sale.id,
        serie=_SERIE,
        numero=numero,
        numero_completo=f"{_SERIE}-{numero:06d}",
        subtotal_centavos=sale.subtotal_centavos,
        iva_total_centavos=sale.iva_total_centavos,
        total_centavos=sale.total_centavos,
        metodo_pago=metodo_pago,
        wompi_transaction_id=wompi_transaction_id,
    )
    invoice_repository.add(session, invoice)
    return invoice


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
    es_wompi = data.metodo_pago in WOMPI_METHODS

    # 2) Crear la venta (con totales coherentes con el CHECK total = subtotal + iva).
    # Wompi: nace 'pendiente_pago' (la confirma el webhook). Local: se cobra ya.
    sale = Sale(
        cash_session_id=cash.id,
        user_id=user_id,
        customer_doc=data.customer_doc,
        customer_nombre=data.customer_nombre,
        subtotal_centavos=totals.subtotal_centavos,
        iva_total_centavos=totals.iva_total_centavos,
        total_centavos=totals.total_centavos,
        status=SaleStatus.pendiente_pago if es_wompi else SaleStatus.pendiente,
        metodo_pago=data.metodo_pago,
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
                costo_unitario_snapshot_centavos=product.precio_costo_centavos,
                iva_rate_snapshot=product.iva,
                iva_bps_snapshot=lt.iva_bps,
                base_centavos=lt.base_centavos,
                iva_centavos=lt.iva_centavos,
                total_linea_centavos=lt.total_linea_centavos,
            ),
        )

    # 4) Cierre del cobro.
    if es_wompi:
        # Pago asíncrono: el stock queda RESERVADO, pero NO se numera factura ni
        # se marca pagada hasta que el webhook confirme (numeración sin huecos:
        # un pago rechazado no consume número). El pago se inicia con POST /payments.
        session.commit()
        session.refresh(sale)
        return sale

    # Cobro local (efectivo/transferencia): factura + pagada en el mismo commit.
    emit_invoice(session, sale, metodo_pago=data.metodo_pago)
    sale.status = SaleStatus.pagada
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


def sale_detail(session: Session, sale_id: int) -> tuple[Sale, list[SaleItem], Invoice | None]:
    """Detalle de la venta. `invoice` es None mientras el pago Wompi no se
    confirma (venta `pendiente_pago`) o si fue `rechazada`."""
    sale = get_sale(session, sale_id)
    items = sale_repository.items_for_sale(session, sale_id)
    invoice = invoice_repository.get_by_sale(session, sale_id)
    return sale, items, invoice
