"""Tests de analítica: corrección de agregaciones, filtros, comparativa, permisos.

Dataset pequeño y controlado (fechas fijas) insertado directo, NO el seed masivo.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.cash_register_session import CashRegisterSession, CashSessionStatus
from app.models.product import IvaRate, Product
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.user import User
from app.services import sale_pricing


def _producto(
    session: Session, *, sku: str, venta: int, costo: int, iva=IvaRate.tarifa_19
) -> Product:
    p = Product(
        nombre=sku,
        sku=sku,
        precio_venta_centavos=venta,
        precio_costo_centavos=costo,
        iva=iva,
        stock_milesimas=1_000_000,
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


def test_summary_cuadra_con_los_datos(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="A", venta=100000, costo=60000)  # IVA 19%
    caja = _caja(session, admin_user.id, datetime(2026, 3, 15, 12))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 15, 12),
    )
    res = client.get(
        "/analytics/summary?desde=2026-03-15&hasta=2026-03-15&comparar=false",
        headers=admin_headers,
    ).json()
    assert res["ventas_centavos"] == 119000  # base 100000 + IVA 19000
    assert res["subtotal_centavos"] == 100000
    assert res["iva_centavos"] == 19000
    assert res["n_transacciones"] == 1
    assert res["ticket_promedio_centavos"] == 119000
    assert res["cogs_centavos"] == 60000
    assert res["margen_centavos"] == 40000  # 100000 - 60000
    assert res["margen_bps"] == 4000


def test_filtro_temporal_excluye_fuera_de_rango(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="B", venta=100000, costo=50000, iva=IvaRate.exento)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
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
        dt=datetime(2026, 4, 10, 10),
    )
    res = client.get(
        "/analytics/summary?desde=2026-03-01&hasta=2026-03-31&comparar=false",
        headers=admin_headers,
    ).json()
    assert res["n_transacciones"] == 1  # solo la de marzo


def test_solo_ventas_pagadas_cuentan(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="C", venta=100000, costo=50000, iva=IvaRate.exento)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 15, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 15, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.tarjeta,
        dt=datetime(2026, 3, 15, 11),
        status=SaleStatus.pendiente_pago,
    )
    res = client.get(
        "/analytics/summary?desde=2026-03-15&hasta=2026-03-15&comparar=false",
        headers=admin_headers,
    ).json()
    assert res["n_transacciones"] == 1  # la pendiente_pago no entra


def test_comparativa_periodo_anterior(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="D", venta=100000, costo=50000, iva=IvaRate.exento)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 1, 10))
    # Periodo anterior (1-2 mar): 1 venta. Periodo actual (3-4 mar): 2 ventas.
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 1, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 3, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 4, 10),
    )
    res = client.get(
        "/analytics/summary?desde=2026-03-03&hasta=2026-03-04", headers=admin_headers
    ).json()
    assert res["n_transacciones"] == 2
    assert res["comparativa"]["n_transacciones"] == 1  # periodo anterior (1-2 mar)
    assert res["comparativa"]["delta_transacciones_bps"] == 10000  # +100%


def test_top_products_y_by_method(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    a = _producto(session, sku="TOP", venta=200000, costo=100000, iva=IvaRate.exento)
    b = _producto(session, sku="LOW", venta=50000, costo=20000, iva=IvaRate.exento)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 15, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(a, 3000)],
        metodo=PaymentMethod.tarjeta,
        dt=datetime(2026, 3, 15, 10),
    )
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(b, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 15, 11),
    )
    q = "desde=2026-03-15&hasta=2026-03-15"
    top = client.get(f"/analytics/top-products?{q}", headers=admin_headers).json()
    assert top[0]["nombre"] == "TOP" and top[0]["ventas_centavos"] == 600000
    metodos = {
        m["metodo"]: m["n_transacciones"]
        for m in client.get(f"/analytics/by-method?{q}", headers=admin_headers).json()
    }
    assert metodos == {"tarjeta": 1, "efectivo": 1}


def test_rango_invalido_da_422(client: TestClient, admin_headers: dict) -> None:
    res = client.get("/analytics/summary?desde=2026-03-31&hasta=2026-03-01", headers=admin_headers)
    assert res.status_code == 422


def test_analytics_solo_admin(
    client: TestClient, admin_headers: dict, cajero_headers: dict
) -> None:
    assert client.get("/analytics/summary", headers=admin_headers).status_code == 200
    assert client.get("/analytics/summary", headers=cajero_headers).status_code == 403
    assert client.get("/analytics/summary").status_code == 401


def test_export_csv(
    client: TestClient, admin_user: User, admin_headers: dict, session: Session
) -> None:
    p = _producto(session, sku="CSV", venta=100000, costo=50000, iva=IvaRate.exento)
    caja = _caja(session, admin_user.id, datetime(2026, 3, 15, 10))
    _venta(
        session,
        user_id=admin_user.id,
        cash_id=caja.id,
        items=[(p, 1000)],
        metodo=PaymentMethod.efectivo,
        dt=datetime(2026, 3, 15, 10),
    )
    res = client.get(
        "/analytics/export.csv?dataset=summary&desde=2026-03-15&hasta=2026-03-15",
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "attachment" in res.headers["content-disposition"]
    assert "ventas" in res.text and "100000" in res.text
