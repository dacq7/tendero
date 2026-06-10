"""Tests de la analítica profesional (Fase 5.2).

Cada agregación se valida contra datos controlados e insertados a mano (fechas
fijas), NO el seed masivo. Verifica que las fórmulas cuadran: márgenes,
contribución, matriz estrella/perro, rotación anualizada (número sensato),
días de inventario, capital inmovilizado, proveedores, clientes y tendencias.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.cash_register_session import CashRegisterSession, CashSessionStatus
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import IvaRate, Product
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier
from app.models.user import User
from app.services import sale_pricing


def _proveedor(session: Session, *, nombre: str, nit: str) -> Supplier:
    s = Supplier(nombre=nombre, nit=nit)
    session.add(s)
    session.flush()
    return s


def _producto(
    session: Session,
    *,
    sku: str,
    venta: int,
    costo: int,
    iva=IvaRate.exento,
    categoria: str | None = None,
    supplier_id: int | None = None,
    stock: int = 1_000_000,
    minimo: int = 0,
) -> Product:
    p = Product(
        nombre=sku,
        sku=sku,
        precio_venta_centavos=venta,
        precio_costo_centavos=costo,
        iva=iva,
        categoria=categoria,
        supplier_id=supplier_id,
        stock_milesimas=stock,
        stock_minimo_milesimas=minimo,
    )
    session.add(p)
    session.flush()
    return p


def _caja(session: Session, user_id: int, dt: datetime) -> CashRegisterSession:
    c = CashRegisterSession(
        user_id=user_id,
        status=CashSessionStatus.cerrada,
        monto_inicial_centavos=0,
        abierta_at=dt,
    )
    session.add(c)
    session.flush()
    return c


def _venta(
    session: Session,
    *,
    user_id: int,
    cash_id: int,
    items: list[tuple[Product, int]],
    metodo: PaymentMethod,
    dt: datetime,
    status: SaleStatus = SaleStatus.pagada,
    customer_doc: str | None = None,
    customer_nombre: str | None = None,
) -> Sale:
    lts = [sale_pricing.line_totals(p.precio_venta_centavos, p.iva, c) for p, c in items]
    totals = sale_pricing.sale_totals(lts)
    sale = Sale(
        cash_session_id=cash_id,
        user_id=user_id,
        subtotal_centavos=totals.subtotal_centavos,
        iva_total_centavos=totals.iva_total_centavos,
        total_centavos=totals.total_centavos,
        status=status,
        metodo_pago=metodo,
        customer_doc=customer_doc,
        customer_nombre=customer_nombre,
        created_at=dt,
        paid_at=dt if status == SaleStatus.pagada else None,
    )
    session.add(sale)
    session.flush()
    for (p, c), lt in zip(items, lts, strict=True):
        session.add(
            SaleItem(
                sale_id=sale.id,
                product_id=p.id,
                nombre_snapshot=p.nombre,
                sku_snapshot=p.sku,
                cantidad_milesimas=c,
                precio_unitario_centavos=p.precio_venta_centavos,
                costo_unitario_snapshot_centavos=p.precio_costo_centavos,
                iva_rate_snapshot=p.iva,
                iva_bps_snapshot=lt.iva_bps,
                base_centavos=lt.base_centavos,
                iva_centavos=lt.iva_centavos,
                total_linea_centavos=lt.total_linea_centavos,
            )
        )
    session.commit()
    return sale


def _movimiento(
    session: Session,
    *,
    product_id: int,
    user_id: int,
    tipo: MovementType,
    cantidad: int,
    dt: datetime,
    costo: int | None = None,
    resultante: int = 0,
) -> None:
    session.add(
        InventoryMovement(
            product_id=product_id,
            tipo=tipo,
            cantidad_milesimas=cantidad,
            costo_unitario_centavos=costo,
            stock_resultante_milesimas=resultante,
            user_id=user_id,
            created_at=dt,
        )
    )
    session.commit()


# ───────────────────────── Rentabilidad ─────────────────────────


def test_profit_products_margen_y_contribucion(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    a = _producto(session, sku="A", venta=100000, costo=60000)
    b = _producto(session, sku="B", venta=50000, costo=40000)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(a, 2000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 10, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(b, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 11, 10),
    )
    q = "desde=2026-03-01&hasta=2026-03-31"
    filas = {
        f["nombre"]: f
        for f in client.get(f"/analytics/profit-products?{q}", headers=admin_headers).json()
    }
    # A: ventas 200000, cogs 120000, margen 80000, bps 4000.
    assert filas["A"]["ventas_centavos"] == 200000
    assert filas["A"]["margen_centavos"] == 80000
    assert filas["A"]["margen_bps"] == 4000
    # B: margen 10000, bps 2000.
    assert filas["B"]["margen_centavos"] == 10000
    assert filas["B"]["margen_bps"] == 2000
    # Contribución: total margen 90000 → A 80000/90000, B 10000/90000.
    assert filas["A"]["contribucion_bps"] == 80000 * 10000 // 90000
    assert filas["B"]["contribucion_bps"] == 10000 * 10000 // 90000


def test_profit_categories_agrupa(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    a = _producto(session, sku="A", venta=100000, costo=60000, categoria="Bebidas")
    b = _producto(session, sku="B", venta=100000, costo=70000, categoria="Bebidas")
    c = _producto(session, sku="C", venta=100000, costo=50000, categoria="Aseo")
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    for p in (a, b, c):
        _venta(
            session,
            user_id=admin_user.id,
            cash_id=caja.id,
            items=[(p, 1000)],
            metodo=PaymentMethod.efectivo,
            dt=datetime(2026, 3, 10, 10),
        )
    q = "desde=2026-03-01&hasta=2026-03-31"
    cats = {
        f["categoria"]: f
        for f in client.get(f"/analytics/profit-categories?{q}", headers=admin_headers).json()
    }
    # Bebidas: ventas 200000, margen (40000+30000)=70000.
    assert cats["Bebidas"]["ventas_centavos"] == 200000
    assert cats["Bebidas"]["margen_centavos"] == 70000
    assert cats["Aseo"]["margen_centavos"] == 50000


def test_profit_matrix_cuadrantes(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    # A: alto volumen + alto margen (estrella); B: bajo volumen + bajo margen (perro).
    a = _producto(session, sku="A", venta=100000, costo=60000)  # bps 4000
    b = _producto(session, sku="B", venta=50000, costo=40000)  # bps 2000
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(a, 2000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 10, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(b, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 11, 10),
    )
    q = "desde=2026-03-01&hasta=2026-03-31"
    m = client.get(f"/analytics/profit-matrix?{q}", headers=admin_headers).json()
    cuad = {i["nombre"]: i["cuadrante"] for i in m["items"]}
    assert cuad["A"] == "estrella"
    assert cuad["B"] == "perro"
    assert m["umbral_volumen_milesimas"] == 1500  # mediana de [2000,1000]
    assert m["umbral_margen_bps"] == 3000  # mediana de [4000,2000]


# ───────────────────────── Inventario ─────────────────────────


def test_inventory_rotation_anualizada_y_capital_inmovilizado(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    # R: stock 10u × $50000 = stock_val 500000. Vende 120u en el año → cogs 6.000.000.
    # Periodo de 365 días ⇒ cogs_anual = cogs. rotación = 6.000.000/500.000 = 12.00 veces/año.
    r = _producto(session, sku="R", venta=80000, costo=50000, stock=10_000)
    # Z: stock 4u × $25000 = 100000, sin ventas ⇒ capital inmovilizado.
    _producto(session, sku="Z", venta=40000, costo=25000, stock=4_000)
    caja = _caja(session, admin_user.id, datetime(2025, 1, 1, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(r, 120_000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2025, 6, 15, 10),
    )
    q = "desde=2025-01-01&hasta=2025-12-31"
    res = client.get(f"/analytics/inventory-rotation?{q}", headers=admin_headers).json()
    por = {p["nombre"]: p for p in res["por_producto"]}
    assert por["R"]["rotacion_centi"] == 1200  # 12.00 veces/año
    assert por["R"]["dias_inventario"] == 30  # 365/12 ≈ 30 días
    assert por["Z"]["rotacion_centi"] == 0  # no rota (0 veces/año)
    assert por["Z"]["dias_inventario"] is None  # sin ventas, no se puede estimar
    # Capital inmovilizado: solo Z (R rota a 30 días, < 180).
    assert res["capital_inmovilizado_centavos"] == 100000


def test_stockouts_y_low_stock(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    _producto(session, sku="P", venta=10000, costo=5000, stock=500, minimo=1000)
    otro = _producto(session, sku="Q", venta=10000, costo=5000, stock=5000, minimo=1000)
    # Q tocó cero dos veces en el rango.
    _movimiento(
        session,
        product_id=otro.id,
        user_id=admin_user.id,
        tipo=MovementType.salida,
        cantidad=1000,
        dt=datetime(2026, 3, 5, 10),
        resultante=0,
    )
    _movimiento(
        session,
        product_id=otro.id,
        user_id=admin_user.id,
        tipo=MovementType.salida,
        cantidad=1000,
        dt=datetime(2026, 3, 9, 10),
        resultante=0,
    )
    q = "desde=2026-03-01&hasta=2026-03-31"
    so = {
        r["nombre"]: r
        for r in client.get(f"/analytics/stockouts?{q}", headers=admin_headers).json()
    }
    assert so["Q"]["veces_en_cero"] == 2
    # P está bajo el mínimo (500 <= 1000).
    low = {r["nombre"] for r in client.get("/analytics/low-stock", headers=admin_headers).json()}
    assert "P" in low and "Q" not in low


def test_reorder_sugiere_productos_que_rotan_y_estan_bajos(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    # Bajo mínimo y con ventas en el periodo ⇒ sugiere recompra.
    p = _producto(session, sku="P", venta=10000, costo=5000, stock=500, minimo=1000)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 30_000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 10, 10),
    )
    q = "desde=2026-03-01&hasta=2026-03-30"  # 30 días, vendió 30u ⇒ 1u/día
    re = {
        r["nombre"]: r for r in client.get(f"/analytics/reorder?{q}", headers=admin_headers).json()
    }
    assert "P" in re
    # Objetivo 30 días = 30u (30000), stock 500 ⇒ sugiere 29500.
    assert re["P"]["cantidad_sugerida_milesimas"] == 29_500


# ───────────────────────── Proveedores ─────────────────────────


def test_suppliers_purchases_y_margen(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    s1 = _proveedor(session, nombre="Distri Uno", nit="DEMO-1")
    s2 = _proveedor(session, nombre="Distri Dos", nit="DEMO-2")
    p1 = _producto(session, sku="P1", venta=100000, costo=60000, supplier_id=s1.id)
    p2 = _producto(session, sku="P2", venta=50000, costo=30000, supplier_id=s2.id)
    # Entradas (compras).
    _movimiento(
        session,
        product_id=p1.id,
        user_id=admin_user.id,
        tipo=MovementType.entrada,
        cantidad=5000,
        costo=60000,
        dt=datetime(2026, 3, 2, 10),
        resultante=5000,
    )
    _movimiento(
        session,
        product_id=p2.id,
        user_id=admin_user.id,
        tipo=MovementType.entrada,
        cantidad=2000,
        costo=30000,
        dt=datetime(2026, 3, 2, 10),
        resultante=2000,
    )
    # Ventas (margen).
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p1, 3000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 10, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p2, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 11, 10),
    )
    q = "desde=2026-03-01&hasta=2026-03-31"
    compras = {
        r["nombre"]: r
        for r in client.get(f"/analytics/suppliers/purchases?{q}", headers=admin_headers).json()
    }
    assert compras["Distri Uno"]["compras_centavos"] == 300000  # 60000×5
    assert compras["Distri Dos"]["compras_centavos"] == 60000  # 30000×2
    margen = {
        r["nombre"]: r
        for r in client.get(f"/analytics/suppliers/margin?{q}", headers=admin_headers).json()
    }
    assert margen["Distri Uno"]["margen_centavos"] == 120000  # (100000-60000)×3
    conc = client.get(f"/analytics/suppliers/concentration?{q}", headers=admin_headers).json()
    assert conc["n_proveedores"] == 2
    # Ventas: Uno 300000, Dos 50000 ⇒ total 350000. top1 = 300000/350000.
    assert conc["concentracion_top1_bps"] == 300000 * 10000 // 350000


# ───────────────────────── Clientes ─────────────────────────


def test_top_customers_y_segmentos(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="P", venta=100000, costo=50000)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    # Cliente recurrente 1098765432: 2 compras. Otro: 1 compra. 1 anónima.
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 5, 10),
        customer_doc="1098765432",
        customer_nombre="Ana",
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 6, 10),
        customer_doc="1098765432",
        customer_nombre="Ana",
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 7, 10),
        customer_doc="222333",
        customer_nombre="Beto",
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 8, 10),
    )  # anónima
    q = "desde=2026-03-01&hasta=2026-03-31"
    top = client.get(f"/analytics/customers/top?{q}", headers=admin_headers).json()
    # Habeas Data: el documento sale enmascarado (solo últimos 4 dígitos).
    assert top[0]["customer_doc"] == "···5432"
    assert top[0]["nombre"] == "Ana"
    assert top[0]["n_compras"] == 2
    assert top[0]["gasto_centavos"] == 200000
    seg = client.get(f"/analytics/customers/segments?{q}", headers=admin_headers).json()
    # Identificados: 3 transacciones (111×2 + 222). Anónimo: 1.
    assert seg["identificado"]["n_transacciones"] == 3
    assert seg["anonimo"]["n_transacciones"] == 1
    assert seg["anonimo"]["ticket_promedio_centavos"] == 100000


# ───────────────────────── Tendencias ─────────────────────────


def test_growth_yoy(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="P", venta=100000, costo=50000)
    caja = _caja(session, admin_user.id, datetime(2025, 1, 1, 10))
    # Marzo 2025: 1 venta (100000). Marzo 2026: 2 ventas (200000).
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2025, 3, 10, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 10, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 11, 10),
    )
    q = "desde=2025-01-01&hasta=2026-03-31"
    g = {
        f["periodo"][:7]: f
        for f in client.get(f"/analytics/growth?{q}", headers=admin_headers).json()
    }
    assert g["2025-03"]["ventas_centavos"] == 100000
    assert g["2026-03"]["ventas_centavos"] == 200000
    assert g["2026-03"]["yoy_bps"] == 10000  # +100% vs mar-2025
    assert g["2025-03"]["yoy_bps"] is None  # no hay 2024


def test_ticket_by_hour_y_dow(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="P", venta=100000, costo=50000)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    # 2 ventas a las 10h, 1 a las 15h.
    for h in (10, 10, 15):
        _venta(
            session,
            user_id=admin_user.id,
            cash_id=caja.id,
            items=[(p, 1000)],
            metodo=PaymentMethod.efectivo,
            dt=datetime(2026, 3, 10, h),
        )
    q = "desde=2026-03-01&hasta=2026-03-31"
    horas = {
        r["bucket"]: r
        for r in client.get(f"/analytics/ticket-by-hour?{q}", headers=admin_headers).json()
    }
    assert horas[10]["n_transacciones"] == 2
    assert horas[10]["ticket_promedio_centavos"] == 100000
    assert horas[15]["n_transacciones"] == 1


def test_projection_periodo_cerrado_no_estima(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="P", venta=100000, costo=50000)
    caja = _caja(session, admin_user.id, datetime(2025, 3, 1, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2025, 3, 10, 10),
    )
    q = "desde=2025-03-01&hasta=2025-03-31"  # periodo pasado y cerrado
    pr = client.get(f"/analytics/projection?{q}", headers=admin_headers).json()
    assert pr["es_estimacion"] is False
    assert pr["ventas_proyectada_centavos"] == pr["ventas_actual_centavos"] == 100000


# ───────────────────────── Permisos y CSV ─────────────────────────


def test_pro_endpoints_solo_admin(
    client: TestClient, admin_headers: dict, cajero_headers: dict
) -> None:
    for ruta in (
        "profit-products",
        "inventory-rotation",
        "suppliers/margin",
        "customers/top",
        "growth",
    ):
        assert client.get(f"/analytics/{ruta}", headers=admin_headers).status_code == 200
        assert client.get(f"/analytics/{ruta}", headers=cajero_headers).status_code == 403
        assert client.get(f"/analytics/{ruta}").status_code == 401


def test_export_csv_datasets_nuevos(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    a = _producto(session, sku="A", venta=100000, costo=60000)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(a, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 10, 10),
    )
    q = "desde=2026-03-01&hasta=2026-03-31"
    for ds in (
        "profit-products",
        "profit-categories",
        "inventory-rotation",
        "suppliers",
        "customers",
        "growth",
    ):
        res = client.get(f"/analytics/export.csv?dataset={ds}&{q}", headers=admin_headers)
        assert res.status_code == 200, ds
        assert res.headers["content-type"].startswith("text/csv")
