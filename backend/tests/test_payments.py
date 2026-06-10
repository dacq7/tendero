"""Tests de pagos Wompi: flujo asíncrono, webhook idempotente, firma y reverso.

Cobertura crítica (dinero/stock): la venta NO se marca pagada sin confirmación,
el webhook es idempotente y valida firma, y un rechazo revierte el stock.
"""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.config import settings
from app.services import payment_service
from app.services.payments.provider import build_signed_event
from tests.test_sales import abrir_caja, crear_producto_con_stock, vender


def _setup_wompi_sale(
    client: TestClient, admin_headers: dict, *, stock: int = 10000, metodo: str = "tarjeta"
) -> tuple[int, dict, dict]:
    """Crea producto+stock, abre caja, vende por método Wompi e inicia el pago."""
    pid = crear_producto_con_stock(
        client, admin_headers, sku="W1", stock_milesimas=stock, precio_venta_centavos=100000
    )
    abrir_caja(client, admin_headers)
    sale = vender(client, admin_headers, (pid, 1000), metodo=metodo).json()
    payment = client.post("/payments", json={"sale_id": sale["id"]}, headers=admin_headers).json()
    return pid, sale, payment


def _event(payment: dict, status_str: str) -> dict:
    return build_signed_event(
        transaction_id=payment["wompi_transaction_id"],
        status=status_str,
        referencia=payment["referencia"],
        monto_centavos=payment["monto_centavos"],
        events_secret=settings.wompi_events_secret,
    )


# ---------- La venta nace pendiente_pago, sin factura ----------


def test_venta_wompi_nace_pendiente_pago_sin_factura(
    client: TestClient, admin_headers: dict
) -> None:
    pid, sale, payment = _setup_wompi_sale(client, admin_headers)
    assert sale["status"] == "pendiente_pago"
    assert sale["invoice"] is None
    assert payment["status"] == "pending"
    assert payment["provider"] == "mock"
    # Stock reservado (descontado al crear).
    assert client.get(f"/products/{pid}", headers=admin_headers).json()["stock_milesimas"] == 9000


def test_start_payment_idempotente(client: TestClient, admin_headers: dict) -> None:
    _pid, sale, payment = _setup_wompi_sale(client, admin_headers)
    again = client.post("/payments", json={"sale_id": sale["id"]}, headers=admin_headers).json()
    assert again["id"] == payment["id"]  # mismo pago, no se duplica


# ---------- Webhook approved ----------


def test_webhook_approved_marca_pagada_y_numera_factura(
    client: TestClient, admin_headers: dict
) -> None:
    _pid, sale, payment = _setup_wompi_sale(client, admin_headers)
    res = client.post("/webhooks/wompi", json=_event(payment, "APPROVED"))
    assert res.status_code == 200

    detail = client.get(f"/sales/{sale['id']}", headers=admin_headers).json()
    assert detail["status"] == "pagada"
    assert detail["invoice"]["numero_completo"] == "POS-000001"
    pago = client.get(f"/payments/by-sale/{sale['id']}", headers=admin_headers).json()
    assert pago["status"] == "approved"


def test_webhook_idempotente_mismo_evento_dos_veces(
    client: TestClient, admin_headers: dict
) -> None:
    _pid, sale, payment = _setup_wompi_sale(client, admin_headers)
    evento = _event(payment, "APPROVED")
    assert client.post("/webhooks/wompi", json=evento).status_code == 200
    # Reprocesar el MISMO evento: un solo efecto.
    assert client.post("/webhooks/wompi", json=evento).status_code == 200

    facturas = client.get("/invoices", headers=admin_headers).json()
    assert len(facturas) == 1  # no se duplicó la factura
    # El número no avanzó: la siguiente venta local toma POS-000002.
    detail = client.get(f"/sales/{sale['id']}", headers=admin_headers).json()
    assert detail["invoice"]["numero_completo"] == "POS-000001"


def test_webhook_idempotente_bajo_concurrencia(
    client: TestClient, _engine: Engine, admin_headers: dict
) -> None:
    _pid, _sale, payment = _setup_wompi_sale(client, admin_headers)
    evento = _event(payment, "APPROVED")

    def procesar() -> None:
        # Cada hilo con su propia sesión: ejercita el SAVEPOINT + UNIQUE.
        with Session(_engine) as s:
            payment_service.process_webhook(s, evento)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for f in [pool.submit(procesar), pool.submit(procesar)]:
            f.result()  # propaga excepciones

    # Un solo efecto: exactamente una factura, pago aprobado una vez.
    assert len(client.get("/invoices", headers=admin_headers).json()) == 1
    pago = client.get(f"/payments/{payment['id']}", headers=admin_headers).json()
    assert pago["status"] == "approved"


def test_webhook_firma_invalida_da_400_sin_efecto(client: TestClient, admin_headers: dict) -> None:
    _pid, sale, payment = _setup_wompi_sale(client, admin_headers)
    evento = _event(payment, "APPROVED")
    evento["data"]["transaction"]["amount_in_cents"] = 1  # rompe el checksum
    res = client.post("/webhooks/wompi", json=evento)
    assert res.status_code == 400
    # Sin efecto: la venta sigue pendiente_pago, sin factura.
    detail = client.get(f"/sales/{sale['id']}", headers=admin_headers).json()
    assert detail["status"] == "pendiente_pago"
    assert detail["invoice"] is None


# ---------- Webhook declined: reverso de stock, sin número ----------


def test_webhook_declined_revierte_stock_y_no_consume_numero(
    client: TestClient, admin_headers: dict
) -> None:
    pid, sale, payment = _setup_wompi_sale(client, admin_headers)  # stock 10000 → 9000
    res = client.post("/webhooks/wompi", json=_event(payment, "DECLINED"))
    assert res.status_code == 200

    detail = client.get(f"/sales/{sale['id']}", headers=admin_headers).json()
    assert detail["status"] == "rechazada"
    assert detail["invoice"] is None
    # Stock revertido a 10000.
    assert client.get(f"/products/{pid}", headers=admin_headers).json()["stock_milesimas"] == 10000
    # Número NO consumido: una venta local válida toma POS-000001.
    ok = vender(client, admin_headers, (pid, 1000), metodo="efectivo")
    assert ok.json()["invoice"]["numero_completo"] == "POS-000001"


# ---------- La venta NO se paga sin webhook ----------


def test_venta_no_pagada_sin_webhook(client: TestClient, admin_headers: dict) -> None:
    _pid, sale, _payment = _setup_wompi_sale(client, admin_headers)
    detail = client.get(f"/sales/{sale['id']}", headers=admin_headers).json()
    assert detail["status"] == "pendiente_pago"
    assert detail["paid_at"] is None
    assert detail["invoice"] is None


def test_cierre_caja_bloqueado_con_pago_en_vuelo(client: TestClient, admin_headers: dict) -> None:
    _pid, _sale, _payment = _setup_wompi_sale(client, admin_headers)
    caja = client.get("/cash/sessions/current", headers=admin_headers).json()["id"]
    res = client.post(
        f"/cash/sessions/{caja}/close",
        json={"efectivo_contado_centavos": 0},
        headers=admin_headers,
    )
    assert res.status_code == 409  # no se cierra con pago Wompi en vuelo


# ---------- Permisos ----------


def test_cajero_no_paga_venta_de_otro(
    client: TestClient, admin_headers: dict, cajero_headers: dict
) -> None:
    _pid, sale, _payment = _setup_wompi_sale(client, admin_headers)
    res = client.post("/payments", json={"sale_id": sale["id"]}, headers=cajero_headers)
    assert res.status_code in (403, 409)  # SaleNotPayable (no es suya)


def test_simulate_solo_en_mock(client: TestClient, admin_headers: dict, monkeypatch) -> None:
    _pid, _sale, payment = _setup_wompi_sale(client, admin_headers)
    # En modo mock: simula y aprueba.
    res = client.post(
        f"/payments/{payment['id']}/simulate",
        json={"result": "approved"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    # En modo 'real' el endpoint no existe (404).
    monkeypatch.setattr(settings, "wompi_provider", "real")
    res2 = client.post(
        f"/payments/{payment['id']}/simulate",
        json={"result": "approved"},
        headers=admin_headers,
    )
    assert res2.status_code == 404


def test_webhook_no_requiere_auth(client: TestClient, admin_headers: dict) -> None:
    _pid, _sale, payment = _setup_wompi_sale(client, admin_headers)
    # Sin token: el webhook es público (200), no 401.
    assert client.post("/webhooks/wompi", json=_event(payment, "APPROVED")).status_code == 200
