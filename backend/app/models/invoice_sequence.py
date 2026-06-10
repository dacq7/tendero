"""Secuencia transaccional de numeración de facturas, por serie.

El número se asigna con SELECT ... FOR UPDATE dentro de la MISMA transacción de
la venta: consecutivo sin huecos (si la venta hace rollback, el número no se
consume) y sin duplicados. En Fase 4 cada resolución DIAN será una serie con su
prefijo y rango [desde, hasta].
"""

from sqlmodel import Field, SQLModel


class InvoiceSequence(SQLModel, table=True):
    __tablename__ = "invoice_sequences"

    serie: str = Field(primary_key=True, max_length=20)
    last_numero: int = Field(default=0)
