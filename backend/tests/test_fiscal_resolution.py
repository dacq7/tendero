"""Tests de resoluciones DIAN: numeración (concurrencia), agotamiento, vigencia."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.services import fiscal_service
from tests.test_fiscal import _factura_pagada


def _nueva_resolucion(client: TestClient, admin_headers: dict, **over) -> dict:
    payload = {
        "numero_resolucion": "RES-1",
        "prefijo": "TEST",
        "numero_desde": 1,
        "numero_hasta": 1000,
        "vigencia_desde": "2020-01-01",
        "vigencia_hasta": "2035-12-31",
        "rut_nit": "900000000-0",
        "responsabilidad": "52",
        "activa": True,
    }
    payload.update(over)
    return client.post("/fiscal/resolutions", json=payload, headers=admin_headers).json()


def test_activar_nueva_desactiva_la_anterior(client: TestClient, admin_headers: dict) -> None:
    _nueva_resolucion(client, admin_headers)  # desactiva la demo SETP
    resoluciones = client.get("/fiscal/resolutions", headers=admin_headers).json()
    activas = [r for r in resoluciones if r["activa"]]
    assert len(activas) == 1
    assert activas[0]["prefijo"] == "TEST"


def test_emite_desde_la_resolucion_activa(client: TestClient, admin_headers: dict) -> None:
    _nueva_resolucion(client, admin_headers, prefijo="ABC", numero_desde=500)
    inv = _factura_pagada(client, admin_headers)
    emision = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers).json()
    assert emision["numero_fiscal_completo"] == "ABC500"


def test_rango_agotado_da_409(client: TestClient, admin_headers: dict) -> None:
    _nueva_resolucion(client, admin_headers, numero_desde=1, numero_hasta=1)  # 1 solo número
    inv1 = _factura_pagada(client, admin_headers, sku="E1")
    inv2 = _factura_pagada(client, admin_headers, sku="E2")
    assert client.post(f"/fiscal/invoices/{inv1}/emit", headers=admin_headers).status_code == 200
    res = client.post(f"/fiscal/invoices/{inv2}/emit", headers=admin_headers)
    assert res.status_code == 409  # ResolutionExhausted


def test_resolucion_fuera_de_vigencia_da_409(client: TestClient, admin_headers: dict) -> None:
    _nueva_resolucion(
        client, admin_headers, vigencia_desde="2019-01-01", vigencia_hasta="2020-12-31"
    )
    inv = _factura_pagada(client, admin_headers)
    res = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers)
    assert res.status_code == 409  # ResolutionExpired


def test_sin_resolucion_activa_da_409(client: TestClient, admin_headers: dict) -> None:
    # Desactivar la demo (la única activa) directamente vía PATCH.
    demo = client.get("/fiscal/resolutions", headers=admin_headers).json()[0]
    client.patch(f"/fiscal/resolutions/{demo['id']}", json={"activa": False}, headers=admin_headers)
    inv = _factura_pagada(client, admin_headers)
    res = client.post(f"/fiscal/invoices/{inv}/emit", headers=admin_headers)
    assert res.status_code == 409  # NoActiveResolution


def test_numeracion_fiscal_sin_duplicados_bajo_concurrencia(
    client: TestClient, _engine: Engine, admin_headers: dict
) -> None:
    inv1 = _factura_pagada(client, admin_headers, sku="C1")
    inv2 = _factura_pagada(client, admin_headers, sku="C2")

    def emitir(invoice_id: int) -> None:
        with Session(_engine) as s:
            fiscal_service.emit_fiscal(s, invoice_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for f in [pool.submit(emitir, inv1), pool.submit(emitir, inv2)]:
            f.result()

    n1 = client.get(f"/fiscal/invoices/{inv1}/emission", headers=admin_headers).json()
    n2 = client.get(f"/fiscal/invoices/{inv2}/emission", headers=admin_headers).json()
    numeros = sorted([n1["numero_fiscal_completo"], n2["numero_fiscal_completo"]])
    assert numeros == ["SETP990000001", "SETP990000002"]  # consecutivos, sin duplicado
