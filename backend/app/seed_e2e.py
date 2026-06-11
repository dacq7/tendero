"""Siembra DETERMINISTA mínima para los tests e2e (Playwright).

Crea/migra una base AISLADA `tendero_e2e` (NUNCA la de desarrollo `tendero` ni la
unit `tendero_test`) y la siembra con datos CONOCIDOS para que los asserts de los
e2e sean estables:

- admin (admin@e2e.co) y cajero (cajero@e2e.co), ambos con clave `E2e1234!`.
- 1 proveedor.
- 4 productos con SKU/precio/stock fijos. `E2E-004` nace por debajo del mínimo para
  ejercitar la alerta de stock bajo. El stock se carga vía MOVIMIENTOS de entrada
  (respeta el invariante: el stock solo cambia por el kardex).
- 1 venta histórica PAGADA en efectivo con su factura POS (para Historial y la
  emisión DIAN, sin depender del flujo de venta del propio test).

Determinista: sin `random` ni `now()` en los valores que se asertan (los timestamps
pueden ser fijos). El aislamiento lo da el DROP/CREATE de la base en cada corrida.

Uso (con DATABASE_URL apuntando a ...tendero_e2e):
    python -m app.seed_e2e
"""

from datetime import datetime
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlmodel import Session

from alembic import command
from app.core.config import settings
from app.core.security import hash_password
from app.models.cash_register_session import CashRegisterSession, CashSessionStatus
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.invoice import Invoice
from app.models.invoice_sequence import InvoiceSequence
from app.models.product import IvaRate, Product, ProductUnit
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.services import sale_pricing

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Credenciales conocidas (solo entorno e2e).
ADMIN_EMAIL = "admin@e2e.co"
CAJERO_EMAIL = "cajero@e2e.co"
E2E_PASSWORD = "E2e1234!"

SERIE = "POS"
# Fecha fija para los timestamps de la venta histórica (no se asertan, pero evitan
# usar now() → reproducible).
FECHA = datetime(2026, 5, 1, 10, 0, 0)

# (nombre, sku, categoria, iva, costo_centavos, venta_centavos, unidad, stock_milesimas)
PRODUCTOS = [
    (
        "Gaseosa E2E",
        "E2E-001",
        "Bebidas",
        IvaRate.tarifa_19,
        120000,
        200000,
        ProductUnit.unidad,
        50000,
    ),
    ("Agua E2E", "E2E-002", "Bebidas", IvaRate.tarifa_19, 60000, 120000, ProductUnit.unidad, 40000),
    ("Arroz E2E", "E2E-003", "Abarrotes", IvaRate.exento, 300000, 420000, ProductUnit.kg, 60000),
    # Nace bajo el mínimo (5 < 30 uds) → dispara la alerta de stock bajo.
    (
        "Stock Bajo E2E",
        "E2E-004",
        "Snacks",
        IvaRate.tarifa_19,
        50000,
        100000,
        ProductUnit.unidad,
        5000,
    ),
]
STOCK_MINIMO = 30000  # ~30 uds


def _e2e_url() -> URL:
    """URL de la base e2e. Guarda: el nombre DEBE terminar en `_e2e` (protege la base
    de desarrollo `tendero` y la unit `tendero_test` de un DROP accidental)."""
    url = make_url(settings.database_url)
    if not url.database or not url.database.endswith("_e2e"):
        raise RuntimeError(
            f"seed_e2e exige una base que termine en '_e2e' (recibida: {url.database!r}). "
            "Apunta DATABASE_URL a la base e2e dedicada."
        )
    return url


def _recreate_database(url: URL) -> None:
    """DROP/CREATE de la base e2e (engine de mantenimiento en autocommit)."""
    admin_url = url.set(database="postgres")
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    dbname = url.database
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ),
            {"db": dbname},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}"'))
        conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    admin.dispose()


def _migrate(url: URL) -> None:
    """Construye el esquema con las migraciones REALES (igual que la suite unit)."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    command.upgrade(cfg, "head")


def _seed(engine: Engine) -> dict:
    with Session(engine) as session:
        # Usuarios conocidos.
        admin = User(
            email=ADMIN_EMAIL,
            full_name="Admin E2E",
            hashed_password=hash_password(E2E_PASSWORD),
            role=UserRole.admin,
        )
        cajero = User(
            email=CAJERO_EMAIL,
            full_name="Cajero E2E",
            hashed_password=hash_password(E2E_PASSWORD),
            role=UserRole.cajero,
        )
        session.add(admin)
        session.add(cajero)

        proveedor = Supplier(nombre="Proveedor E2E", nit="E2E-900100")
        session.add(proveedor)
        session.flush()

        productos: list[Product] = []
        for nombre, sku, cat, iva, costo, venta, unidad, stock in PRODUCTOS:
            p = Product(
                nombre=nombre,
                sku=sku,
                categoria=cat,
                iva=iva,
                unidad=unidad,
                supplier_id=proveedor.id,
                precio_costo_centavos=costo,
                precio_venta_centavos=venta,
                stock_milesimas=stock,
                stock_minimo_milesimas=STOCK_MINIMO,
            )
            session.add(p)
            productos.append(p)
        session.flush()

        # Carga inicial como MOVIMIENTO de entrada por producto (kardex coherente).
        for p in productos:
            session.add(
                InventoryMovement(
                    product_id=p.id,
                    tipo=MovementType.entrada,
                    cantidad_milesimas=p.stock_milesimas,
                    costo_unitario_centavos=p.precio_costo_centavos,
                    stock_resultante_milesimas=p.stock_milesimas,
                    motivo="Carga inicial (e2e)",
                    created_at=FECHA,
                )
            )
        session.flush()

        # Caja cerrada para colgar la venta histórica.
        caja = CashRegisterSession(
            user_id=cajero.id,
            status=CashSessionStatus.cerrada,
            monto_inicial_centavos=10000000,
            abierta_at=FECHA,
            cerrada_at=FECHA,
            closed_by_user_id=cajero.id,
        )
        session.add(caja)
        session.flush()

        # Venta histórica: 1 Gaseosa E2E en efectivo, pagada, con factura POS.
        gaseosa = productos[0]
        cant = 1000  # 1 unidad
        lt = sale_pricing.line_totals(gaseosa.precio_venta_centavos, gaseosa.iva, cant)
        totals = sale_pricing.sale_totals([lt])
        sale = Sale(
            cash_session_id=caja.id,
            user_id=cajero.id,
            subtotal_centavos=totals.subtotal_centavos,
            iva_total_centavos=totals.iva_total_centavos,
            total_centavos=totals.total_centavos,
            status=SaleStatus.pagada,
            metodo_pago=PaymentMethod.efectivo,
            created_at=FECHA,
            paid_at=FECHA,
        )
        session.add(sale)
        session.flush()
        session.add(
            SaleItem(
                sale_id=sale.id,
                product_id=gaseosa.id,
                nombre_snapshot=gaseosa.nombre,
                sku_snapshot=gaseosa.sku,
                cantidad_milesimas=cant,
                precio_unitario_centavos=gaseosa.precio_venta_centavos,
                costo_unitario_snapshot_centavos=gaseosa.precio_costo_centavos,
                iva_rate_snapshot=gaseosa.iva,
                iva_bps_snapshot=lt.iva_bps,
                base_centavos=lt.base_centavos,
                iva_centavos=lt.iva_centavos,
                total_linea_centavos=lt.total_linea_centavos,
            )
        )
        # Descontar el stock vendido como MOVIMIENTO de salida.
        gaseosa.stock_milesimas -= cant
        session.add(
            InventoryMovement(
                product_id=gaseosa.id,
                tipo=MovementType.salida,
                cantidad_milesimas=cant,
                costo_unitario_centavos=gaseosa.precio_costo_centavos,
                stock_resultante_milesimas=gaseosa.stock_milesimas,
                motivo="Venta (e2e)",
                user_id=cajero.id,
                created_at=FECHA,
            )
        )
        session.add(gaseosa)

        # Numeración POS: la migración siembra la serie con last_numero=0.
        seq = session.get(InvoiceSequence, SERIE)
        if seq is None:
            seq = InvoiceSequence(serie=SERIE, last_numero=0)
            session.add(seq)
            session.flush()
        numero = seq.last_numero + 1
        session.add(
            Invoice(
                sale_id=sale.id,
                serie=SERIE,
                numero=numero,
                numero_completo=f"{SERIE}-{numero:06d}",
                subtotal_centavos=totals.subtotal_centavos,
                iva_total_centavos=totals.iva_total_centavos,
                total_centavos=totals.total_centavos,
                metodo_pago=PaymentMethod.efectivo,
                created_at=FECHA,
            )
        )
        seq.last_numero = numero
        session.add(seq)
        session.commit()

        return {
            "admin": ADMIN_EMAIL,
            "cajero": CAJERO_EMAIL,
            "productos": len(productos),
            "factura": f"{SERIE}-{numero:06d}",
        }


def main() -> None:
    url = _e2e_url()
    _recreate_database(url)
    _migrate(url)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        info = _seed(engine)
    finally:
        engine.dispose()
    print(
        f"Seed e2e en {url.database}: admin={info['admin']}, cajero={info['cajero']}, "
        f"{info['productos']} productos, factura {info['factura']}."
    )


if __name__ == "__main__":
    main()
