"""Asignación transaccional del siguiente número de factura. Sin commit.

`next_numero` bloquea la fila de la serie (FOR UPDATE) e incrementa dentro de la
transacción de la venta: consecutivo sin huecos (si la venta hace rollback, el
incremento también se revierte) y sin duplicados.
"""

from sqlmodel import Session, select

from app.models.invoice_sequence import InvoiceSequence


def next_numero(session: Session, serie: str = "POS") -> int:
    stmt = select(InvoiceSequence).where(InvoiceSequence.serie == serie).with_for_update()
    seq = session.exec(stmt).first()
    if seq is None:
        # Defensa: la migración siembra la serie, pero si falta, créala.
        seq = InvoiceSequence(serie=serie, last_numero=0)
        session.add(seq)
        session.flush()
    seq.last_numero += 1
    session.add(seq)
    session.flush()
    return seq.last_numero
