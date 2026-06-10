"""Tests de numeración de facturas: consecutiva, sin huecos ni duplicados,
incluso bajo concurrencia real (dos hilos con sesiones separadas)."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.models.sale import PaymentMethod
from app.repositories import invoice_repository
from app.schemas.sale import SaleCreate, SaleLineCreate
from app.services import sale_service
from tests.test_sales import abrir_caja, crear_producto_con_stock, vender


def test_numeracion_consecutiva_sin_huecos(client: TestClient, admin_headers: dict) -> None:
    pid = crear_producto_con_stock(client, admin_headers, sku="N1", stock_milesimas=100000)
    abrir_caja(client, admin_headers)
    numeros = []
    for _ in range(3):
        sale = vender(client, admin_headers, (pid, 1000)).json()
        numeros.append(sale["invoice"]["numero_completo"])
    assert numeros == ["POS-000001", "POS-000002", "POS-000003"]


def test_una_factura_por_venta(client: TestClient, admin_headers: dict) -> None:
    pid = crear_producto_con_stock(client, admin_headers, sku="N2", stock_milesimas=10000)
    abrir_caja(client, admin_headers)
    sale_id = vender(client, admin_headers, (pid, 1000)).json()["id"]
    invoices = client.get("/invoices", headers=admin_headers).json()
    de_la_venta = [i for i in invoices if i["sale_id"] == sale_id]
    assert len(de_la_venta) == 1


def test_numeracion_sin_duplicados_bajo_concurrencia(
    client: TestClient, _engine: Engine, admin_headers: dict
) -> None:
    # Setup vía API (commitea a la base real): 2 productos con stock + caja abierta.
    p1 = crear_producto_con_stock(client, admin_headers, sku="C1", stock_milesimas=100000)
    p2 = crear_producto_con_stock(client, admin_headers, sku="C2", stock_milesimas=100000)
    abrir_caja(client, admin_headers)
    uid = client.get("/auth/me", headers=admin_headers).json()["id"]

    def vender(product_id: int) -> None:
        # Cada hilo con su PROPIA sesión: ejercita el FOR UPDATE de caja/secuencia.
        with Session(_engine) as s:
            data = SaleCreate(
                lineas=[SaleLineCreate(product_id=product_id, cantidad_milesimas=1000)],
                metodo_pago=PaymentMethod.efectivo,
            )
            sale_service.create_sale(s, data, user_id=uid)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futuros = [pool.submit(vender, p1), pool.submit(vender, p2)]
        for f in futuros:
            f.result()  # propaga cualquier excepción

    with Session(_engine) as s:
        numeros = sorted(inv.numero for inv in invoice_repository.list_all(s))
    assert numeros == [1, 2]  # dos números distintos y consecutivos, sin duplicado
