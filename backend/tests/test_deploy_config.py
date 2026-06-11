"""Verifica la config de arranque para producción (Railway) — Fase 6 B.3.

No despliega nada; comprueba que los artefactos de deploy existen y tienen la forma
correcta para que un fallo evidente (puerto hardcodeado, sin migración) se detecte
en CI y no en producción.
"""

import json
import stat
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_start_sh_migra_y_lee_puerto_de_railway() -> None:
    script = BACKEND_DIR / "start.sh"
    assert script.exists(), "Falta backend/start.sh (arranque de producción)."
    texto = script.read_text()
    # Migra ANTES de servir.
    assert "alembic upgrade head" in texto
    # Lee el $PORT que inyecta Railway y escucha en 0.0.0.0 (no hardcodea 8020).
    assert "${PORT" in texto
    assert "0.0.0.0" in texto
    # Producción: sin --reload.
    assert "--reload" not in texto
    # Ejecutable.
    assert script.stat().st_mode & stat.S_IXUSR, "start.sh debe ser ejecutable."


def test_python_version_fija_312() -> None:
    pv = BACKEND_DIR / ".python-version"
    # Railpack lee `.python-version` (mise-compatible) para fijar la versión.
    assert pv.exists(), "Falta backend/.python-version (Railpack elige la versión)."
    assert pv.read_text().strip() == "3.12"


def test_railway_json_railpack_con_arranque_inline() -> None:
    """Railway usa Railpack; el arranque va INLINE en railway.json (no un script
    suelto, que Railpack puede no incluir en la imagen de runtime). Debe migrar
    antes de servir y leer $PORT en 0.0.0.0."""
    cfg = json.loads((BACKEND_DIR / "railway.json").read_text())
    assert cfg["build"]["builder"] == "RAILPACK"
    start = cfg["deploy"]["startCommand"]
    assert "alembic upgrade head" in start
    assert "uvicorn app.main:app" in start
    assert "0.0.0.0" in start
    assert "${PORT" in start
    # No depende de un script suelto (la causa del fallo original en Railpack).
    assert "start.sh" not in start
