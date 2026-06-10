"""Tests del seed de demo: idempotente, determinista y consistente con el modelo."""

from datetime import datetime

from sqlalchemy.engine import Engine
from sqlmodel import Session, func, select

from app.core.security import hash_password
from app.models.cash_register_session import CashRegisterSession, CashSessionStatus
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.seed_demo import seed_demo


def test_seed_idempotente_y_determinista(_engine: Engine) -> None:
    # Rango corto (1 mes) para un dataset chico pero igual de consistente.
    r1 = seed_demo(db_engine=_engine, meses=1)
    r2 = seed_demo(db_engine=_engine, meses=1)
    assert r1["ventas"] > 0
    assert r2 == r1  # mismo conteo: idempotente (borra-y-recrea) + determinista


def test_reseed_sobre_venta_no_demo_que_referencia_producto_demo(_engine: Engine) -> None:
    """Camino que falló en producción: una venta NO-demo (p. ej. prueba manual)
    referencia un producto demo. Al resembrar, `sale_items.product_id` (RESTRICT)
    bloqueaba el borrado de productos. El wipe debe limpiar esa venta entera y
    resembrar sin error de FK, con conteos idempotentes."""
    primero = seed_demo(db_engine=_engine, meses=1)

    # Inserta una venta de un usuario NO-demo que apunta a un producto demo.
    with Session(_engine) as s:
        prod = s.exec(select(Product).where(Product.sku.like("DEMO-%"))).first()
        assert prod is not None
        intruso = User(
            email="real.admin@tienda.co",  # NO empieza con "demo." → no es demo
            full_name="Admin Real",
            hashed_password=hash_password("Real1234!"),
            role=UserRole.admin,
        )
        s.add(intruso)
        s.flush()
        caja = CashRegisterSession(
            user_id=intruso.id,
            status=CashSessionStatus.cerrada,
            monto_inicial_centavos=0,
            abierta_at=datetime(2026, 5, 1, 8),
        )
        s.add(caja)
        s.flush()
        venta = Sale(
            cash_session_id=caja.id,
            user_id=intruso.id,
            subtotal_centavos=prod.precio_venta_centavos,
            iva_total_centavos=0,
            total_centavos=prod.precio_venta_centavos,
            status=SaleStatus.pagada,
            metodo_pago=PaymentMethod.efectivo,
            created_at=datetime(2026, 5, 1, 10),
            paid_at=datetime(2026, 5, 1, 10),
        )
        s.add(venta)
        s.flush()
        s.add(
            SaleItem(
                sale_id=venta.id,
                product_id=prod.id,  # ← referencia el producto demo (el bloqueo)
                nombre_snapshot=prod.nombre,
                sku_snapshot=prod.sku,
                cantidad_milesimas=1000,
                precio_unitario_centavos=prod.precio_venta_centavos,
                costo_unitario_snapshot_centavos=prod.precio_costo_centavos,
                iva_rate_snapshot=prod.iva,
                iva_bps_snapshot=0,
                base_centavos=prod.precio_venta_centavos,
                iva_centavos=0,
                total_linea_centavos=prod.precio_venta_centavos,
            )
        )
        s.commit()

    # Resembrar NO debe lanzar ForeignKeyViolation (antes fallaba aquí).
    segundo = seed_demo(db_engine=_engine, meses=1)
    assert segundo == primero  # idempotente: mismo conteo, sin duplicar

    with Session(_engine) as s:
        intruso = s.exec(select(User).where(User.email == "real.admin@tienda.co")).first()
        assert intruso is not None  # el usuario NO-demo NO se borra
        sobrevivientes = s.exec(
            select(func.count()).select_from(Sale).where(Sale.user_id == intruso.id)
        ).one()
        assert sobrevivientes == 0  # pero su venta (que referenciaba demo) sí se limpió
        # Ningún sale_item quedó apuntando a un producto inexistente (sin huérfanos).
        huerfanos = s.exec(
            select(func.count())
            .select_from(SaleItem)
            .where(SaleItem.product_id.not_in(select(Product.id)))
        ).one()
        assert huerfanos == 0


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
