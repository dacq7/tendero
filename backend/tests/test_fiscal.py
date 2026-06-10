"""Tests de emisión fiscal DIAN: idempotencia, estados, reintento y permisos."""

from fastapi.testclient import TestClient

from app.models.fiscal_emission import FiscalProvider
from app.models.invoice import DianStatus
from app.services import fiscal_service
from app.services.fiscal.provider import EmissionResult
from tests.test_sales import abrir_caja, crear_producto_con_stock, vender


def _factura_pagada(client: TestClient, admin_headers: dict, *, sku: str = "F1") -> int:
    """Crea una venta local pagada y devuelve el id de su factura interna."""
    pid = crear_producto_con_stock(client, admin_headers, sku=sku, stock_milesimas=10000)
    if client.get("/cash/sessions/current", headers=admin_headers).status_code != 200:
        abrir_caja(client, admin_headers)
    sale = vender(client, admin_headers, (pid, 1000), metodo="efectivo").json()
    return sale["invoice"]["id"]


def test_emit_acepta_y_genera_cufe(client: TestClient, admin_headers: dict) -> None:
    inv = _factura_pagada(client, admin_headers)
    res = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "accepted"
    assert body["cufe"]
    assert body["numero_fiscal_completo"] == "SETP990000001"
    assert body["provider"] == "mock"
    assert body["intentos"] == 1


def test_emit_idempotente_reemitir_aceptada(client: TestClient, admin_headers: dict) -> None:
    inv = _factura_pagada(client, admin_headers)
    first = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers).json()
    again = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers).json()
    # Misma emisión: mismo número fiscal y mismo CUFE, sin reenviar (intentos no sube).
    assert again["numero_fiscal_completo"] == first["numero_fiscal_completo"]
    assert again["cufe"] == first["cufe"]
    assert again["intentos"] == 1


def test_numero_fiscal_consecutivo_sin_huecos(client: TestClient, admin_headers: dict) -> None:
    inv1 = _factura_pagada(client, admin_headers, sku="N1")
    inv2 = _factura_pagada(client, admin_headers, sku="N2")
    n1 = client.post(f"/fiscal/invoices/{inv1}/emit", headers=admin_headers).json()
    n2 = client.post(f"/fiscal/invoices/{inv2}/emit", headers=admin_headers).json()
    assert n1["numero_fiscal_completo"] == "SETP990000001"
    assert n2["numero_fiscal_completo"] == "SETP990000002"


def test_estado_dian_se_refleja_en_la_factura(client: TestClient, admin_headers: dict) -> None:
    inv = _factura_pagada(client, admin_headers)
    assert client.get(f"/invoices/{inv}", headers=admin_headers).json()["dian_status"] == "none"
    client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers)
    factura = client.get(f"/invoices/{inv}", headers=admin_headers).json()
    assert factura["dian_status"] == "accepted"
    assert factura["cufe"]


def test_emit_factura_inexistente_da_404(client: TestClient, admin_headers: dict) -> None:
    assert client.post("/fiscal/invoices/999/emit", headers=admin_headers).status_code == 404


def test_reintento_tras_rechazo_reusa_numero(
    client: TestClient, admin_headers: dict, monkeypatch
) -> None:
    inv = _factura_pagada(client, admin_headers)

    # Proveedor controlado: rechaza la 1ª vez, acepta la 2ª.
    class _FakeProvider:
        name = FiscalProvider.mock

        def __init__(self) -> None:
            self.calls = 0

        def submit(self, doc) -> EmissionResult:
            self.calls += 1
            if self.calls == 1:
                return EmissionResult(DianStatus.rejected, None, None, "rechazo de prueba")
            return EmissionResult(DianStatus.accepted, "CUFE-OK", "doc-1", None)

        def get_status(self, pt_document_id):  # pragma: no cover
            return EmissionResult(DianStatus.accepted, "CUFE-OK", pt_document_id, None)

    fake = _FakeProvider()
    monkeypatch.setattr(fiscal_service, "get_fiscal_provider", lambda: fake)

    rechazada = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers).json()
    assert rechazada["status"] == "rejected"
    assert rechazada["motivo_rechazo"] == "rechazo de prueba"
    numero = rechazada["numero_fiscal_completo"]

    aceptada = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers).json()
    assert aceptada["status"] == "accepted"
    assert aceptada["numero_fiscal_completo"] == numero  # MISMO número (no se quema otro)
    assert aceptada["intentos"] == 2


def test_fallo_del_pt_deja_pending_y_reintento_reusa_numero(
    client: TestClient, admin_headers: dict, monkeypatch
) -> None:
    from app.services.fiscal_errors import FiscalProviderUnavailable

    inv = _factura_pagada(client, admin_headers)

    class _FlakyProvider:
        name = FiscalProvider.mock

        def __init__(self) -> None:
            self.calls = 0

        def submit(self, doc) -> EmissionResult:
            self.calls += 1
            if self.calls == 1:
                raise FiscalProviderUnavailable("PT caído")  # falla TRAS reservar número
            return EmissionResult(DianStatus.accepted, "CUFE-OK", "doc-1", None)

        def get_status(self, pt_document_id):  # pragma: no cover
            return EmissionResult(DianStatus.accepted, "CUFE-OK", pt_document_id, None)

    flaky = _FlakyProvider()
    monkeypatch.setattr(fiscal_service, "get_fiscal_provider", lambda: flaky)

    # 1er intento: el PT falla → 503, pero el número fiscal ya quedó reservado (pending).
    assert client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers).status_code == 503
    pending = client.get(f"/fiscal/invoices/{inv}/emission", headers=admin_headers).json()
    assert pending["status"] == "pending"
    numero = pending["numero_fiscal_completo"]
    assert numero == "SETP990000001"

    # 2º intento: recupera la misma emisión, reusa el número, sin consumir otro.
    aceptada = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers).json()
    assert aceptada["status"] == "accepted"
    assert aceptada["numero_fiscal_completo"] == numero


def test_provider_real_sin_credenciales_da_503(
    client: TestClient, admin_headers: dict, monkeypatch
) -> None:
    from app.core.config import settings

    inv = _factura_pagada(client, admin_headers)
    monkeypatch.setattr(settings, "fiscal_provider", "real")
    monkeypatch.setattr(settings, "fiscal_pt_api_url", "")
    res = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers)
    assert res.status_code == 503


def test_cajero_no_emite_pero_consulta(
    client: TestClient, admin_headers: dict, cajero_headers: dict
) -> None:
    inv = _factura_pagada(client, admin_headers)
    # Cajero no puede emitir.
    assert client.post(f"/fiscal/invoices/{inv}/emit", headers=cajero_headers).status_code == 403
    # Admin emite; cajero puede consultar el estado.
    client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers)
    assert client.get(f"/fiscal/invoices/{inv}/emission", headers=cajero_headers).status_code == 200


def test_cajero_no_gestiona_resoluciones(client: TestClient, cajero_headers: dict) -> None:
    assert client.get("/fiscal/resolutions", headers=cajero_headers).status_code == 403
