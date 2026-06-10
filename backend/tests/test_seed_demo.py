"""Tests del seed de demo: idempotente, determinista y consistente con el modelo."""

from sqlalchemy.engine import Engine
from sqlmodel import Session, func, select

from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier
from app.seed_demo import seed_demo


def test_seed_idempotente_y_determinista(_engine: Engine) -> None:
    # Rango corto (1 mes) para un dataset chico pero igual de consistente.
    r1 = seed_demo(db_engine=_engine, meses=1)
    r2 = seed_demo(db_engine=_engine, meses=1)
    assert r1["ventas"] > 0
    assert r2 == r1  # mismo conteo: idempotente (borra-y-recrea) + determinista


def test_seed_produce_datos_consistentes(_engine: Engine) -> None:
    seed_demo(db_engine=_engine, meses=1)
    with Session(_engine) as s:
        # Todas las ventas del seed son pagadas y con fecha de cobro.
        n = s.exec(select(func.count()).select_from(Sale)).one()
        n_pagadas = s.exec(select(func.count()).where(Sale.status == SaleStatus.pagada)).one()
        assert n_pagadas == n and n > 0
        assert s.exec(select(func.count()).where(Sale.paid_at.is_(None))).one() == 0

        # Totales coherentes: cada venta = suma de sus líneas (sin descuadre).
        ventas = s.exec(select(Sale).limit(20)).all()
        for sale in ventas:
            items = s.exec(select(SaleItem).where(SaleItem.sale_id == sale.id)).all()
            assert sale.subtotal_centavos == sum(i.base_centavos for i in items)
            assert sale.iva_total_centavos == sum(i.iva_centavos for i in items)
            assert sale.total_centavos == sale.subtotal_centavos + sale.iva_total_centavos
            # El costo quedó congelado (snapshot > 0 para márgenes históricos).
            assert all(i.costo_unitario_snapshot_centavos > 0 for i in items)

        # Stock coherente con el kardex: stock final = Σ entradas − Σ salidas.
        productos = s.exec(select(Product)).all()
        for p in productos:
            entradas = s.exec(
                select(func.coalesce(func.sum(InventoryMovement.cantidad_milesimas), 0)).where(
                    InventoryMovement.product_id == p.id,
                    InventoryMovement.tipo == MovementType.entrada,
                )
            ).one()
            salidas = s.exec(
                select(func.coalesce(func.sum(InventoryMovement.cantidad_milesimas), 0)).where(
                    InventoryMovement.product_id == p.id,
                    InventoryMovement.tipo == MovementType.salida,
                )
            ).one()
            assert p.stock_milesimas == entradas - salidas
            # Cada producto demo tiene proveedor asignado.
            assert p.supplier_id is not None

        # Proveedores sembrados y ventas con mezcla de clientes recurrentes/anónimos.
        assert s.exec(select(func.count()).select_from(Supplier)).one() == 5
        identificadas = s.exec(select(func.count()).where(Sale.customer_doc.is_not(None))).one()
        anonimas = s.exec(select(func.count()).where(Sale.customer_doc.is_(None))).one()
        assert identificadas > 0 and anonimas > 0
