"""Venta y sus líneas. La línea guarda SNAPSHOT de precio e IVA (no referencia
viva al producto): el precio/nombre del producto puede cambiar después y la
venta debe conservar lo que se cobró. Dinero en centavos, cantidades en milésimas.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.models.product import IvaRate


class SaleStatus(StrEnum):
    pendiente = "pendiente"  # creada, aún sin cobrar
    pagada = "pagada"  # cobro registrado
    anulada = "anulada"  # reversada (previsto; endpoint no implementado en Fase 2)


class PaymentMethod(StrEnum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    nequi = "nequi"
    transferencia = "transferencia"


class Sale(SQLModel, table=True):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("subtotal_centavos >= 0", name="ck_sales_subtotal_no_neg"),
        CheckConstraint("iva_total_centavos >= 0", name="ck_sales_iva_no_neg"),
        CheckConstraint("total_centavos >= 0", name="ck_sales_total_no_neg"),
        CheckConstraint(
            "total_centavos = subtotal_centavos + iva_total_centavos",
            name="ck_sales_total_coherente",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    cash_session_id: int = Field(
        foreign_key="cash_register_sessions.id", ondelete="RESTRICT", index=True
    )
    user_id: int = Field(foreign_key="users.id", ondelete="RESTRICT", index=True)

    # Cliente opcional (Habeas Data: minimizar; sin tabla Customer en esta fase).
    customer_doc: str | None = Field(default=None, max_length=50)
    customer_nombre: str | None = Field(default=None, max_length=255)

    subtotal_centavos: int = Field(default=0)
    iva_total_centavos: int = Field(default=0)
    total_centavos: int = Field(default=0)

    status: SaleStatus = Field(default=SaleStatus.pendiente, index=True)
    metodo_pago: PaymentMethod | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    paid_at: datetime | None = Field(default=None)


class SaleItem(SQLModel, table=True):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("cantidad_milesimas > 0", name="ck_sale_items_cantidad_pos"),
        CheckConstraint("precio_unitario_centavos >= 0", name="ck_sale_items_precio_no_neg"),
        CheckConstraint("base_centavos >= 0", name="ck_sale_items_base_no_neg"),
        CheckConstraint("iva_centavos >= 0", name="ck_sale_items_iva_no_neg"),
        CheckConstraint("total_linea_centavos >= 0", name="ck_sale_items_total_no_neg"),
    )

    id: int | None = Field(default=None, primary_key=True)
    sale_id: int = Field(foreign_key="sales.id", ondelete="CASCADE", index=True)
    product_id: int = Field(foreign_key="products.id", ondelete="RESTRICT", index=True)

    # Snapshots congelados al momento de la venta.
    nombre_snapshot: str = Field(max_length=255)
    sku_snapshot: str = Field(max_length=64)
    cantidad_milesimas: int
    precio_unitario_centavos: int  # base sin IVA
    iva_rate_snapshot: IvaRate  # preserva exento vs tarifa_0 (para Fase 4)
    iva_bps_snapshot: int  # puntos básicos congelados

    # Cálculo congelado (enteros).
    base_centavos: int
    iva_centavos: int
    total_linea_centavos: int
