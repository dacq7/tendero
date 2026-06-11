"""Hardening Fase 6 B.1 — la configuración exige secretos, sin defaults en código.

Arrancar sin los secretos requeridos debe fallar RUIDOSAMENTE (ValidationError),
no operar en silencio con credenciales conocidas. Estos tests construyen `Settings`
de forma aislada (`_env_file=None`) para no leer el `.env` real del repo.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Secretos que ahora son OBLIGATORIOS (sin valor por defecto en código).
REQUIRED_SECRETS = [
    "DATABASE_URL",
    "JWT_SECRET",
    "WOMPI_INTEGRITY_SECRET",
    "WOMPI_EVENTS_SECRET",
    "FISCAL_CUFE_SECRET",
]

# Un entorno mínimo y válido para construir Settings en los tests positivos.
VALID_ENV = {
    "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5436/tendero",
    "JWT_SECRET": "x" * 32,
    "WOMPI_INTEGRITY_SECRET": "integrity_test_secret",
    "WOMPI_EVENTS_SECRET": "events_test_secret",
    "FISCAL_CUFE_SECRET": "cufe_demo_secret",
}


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quita del entorno los secretos (y APP_ENV) para aislar Settings."""
    for key in [*REQUIRED_SECRETS, "APP_ENV"]:
        monkeypatch.delenv(key, raising=False)


def test_arranca_sin_secretos_falla_ruidoso(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin ningún secreto en el entorno, Settings() lanza ValidationError claro."""
    _clear(monkeypatch)
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)

    faltantes = {err["loc"][0] for err in exc.value.errors()}
    # Los cinco secretos requeridos deben reportarse como faltantes.
    assert faltantes == {s.lower() for s in REQUIRED_SECRETS}


@pytest.mark.parametrize("missing", REQUIRED_SECRETS)
def test_falta_un_solo_secreto_tambien_falla(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    """Quitar CUALQUIERA de los secretos requeridos basta para abortar el arranque."""
    _clear(monkeypatch)
    env = {k: v for k, v in VALID_ENV.items() if k != missing}
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, **{k.lower(): v for k, v in env.items()})

    faltantes = {err["loc"][0] for err in exc.value.errors()}
    assert missing.lower() in faltantes


def test_con_todos_los_secretos_arranca(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con el entorno completo, Settings se construye sin defaults de demo en código."""
    _clear(monkeypatch)
    s = Settings(_env_file=None, **{k.lower(): v for k, v in VALID_ENV.items()})
    assert s.database_url == VALID_ENV["DATABASE_URL"]
    assert s.jwt_secret == VALID_ENV["JWT_SECRET"]
    # app_env conserva un default no sensible (development); no es un secreto.
    assert s.app_env == "development"


def test_produccion_rechaza_secretos_de_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con app_env=production, un secreto placeholder de demo aborta el arranque."""
    _clear(monkeypatch)
    env = dict(VALID_ENV)
    env["WOMPI_EVENTS_SECRET"] = "events_test_secret"  # valor de .env.example
    with pytest.raises(ValidationError) as exc:
        Settings(
            _env_file=None,
            app_env="production",
            **{k.lower(): v for k, v in env.items()},
        )
    assert "WOMPI_EVENTS_SECRET" in str(exc.value)


def test_produccion_acepta_secretos_reales(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con secretos no-demo, producción arranca (HSTS y guardas activas)."""
    _clear(monkeypatch)
    reales = {
        "DATABASE_URL": "postgresql+psycopg://u:p@db/prod",
        "JWT_SECRET": "a-real-64-hex-secret-" + "0" * 40,
        "WOMPI_INTEGRITY_SECRET": "real-integrity-xyz",
        "WOMPI_EVENTS_SECRET": "real-events-xyz",
        "FISCAL_CUFE_SECRET": "real-cufe-xyz",
    }
    s = Settings(_env_file=None, app_env="production", **{k.lower(): v for k, v in reales.items()})
    assert s.app_env == "production"


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Settings:
    """Construye Settings aislado del `.env` real con el entorno mínimo válido."""
    _clear(monkeypatch)
    env = {**VALID_ENV, **{k.upper(): v for k, v in overrides.items()}}
    return Settings(_env_file=None, **{k.lower(): v for k, v in env.items()})


# ---------- CORS multi-origen (deploy Fase 6 B.3) ----------


def test_frontend_origins_un_solo_origen(monkeypatch: pytest.MonkeyPatch) -> None:
    """El default local sigue siendo un único origen (no rompe desarrollo)."""
    s = _settings(monkeypatch, frontend_origin="http://localhost:3001")
    assert s.frontend_origins == ["http://localhost:3001"]


def test_frontend_origins_multiples(monkeypatch: pytest.MonkeyPatch) -> None:
    """Varios orígenes separados por coma → lista saneada (prod + previews)."""
    s = _settings(
        monkeypatch,
        frontend_origin="https://tendero.vercel.app, https://tendero-pr-1.vercel.app",
    )
    assert s.frontend_origins == [
        "https://tendero.vercel.app",
        "https://tendero-pr-1.vercel.app",
    ]


def test_frontend_origins_ignora_vacios(monkeypatch: pytest.MonkeyPatch) -> None:
    """Comas finales o dobles no producen orígenes vacíos."""
    s = _settings(monkeypatch, frontend_origin="https://a.vercel.app,, ,https://b.vercel.app,")
    assert s.frontend_origins == ["https://a.vercel.app", "https://b.vercel.app"]


# ---------- Normalización del driver de Postgres (deploy Fase 6 B.3) ----------


def test_database_url_normaliza_driver_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    """`postgresql://` (lo que entrega Railway) → `postgresql+psycopg://`."""
    s = _settings(monkeypatch, database_url="postgresql://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_database_url_normaliza_driver_postgres_legado(monkeypatch: pytest.MonkeyPatch) -> None:
    """El esquema legado `postgres://` también se normaliza."""
    s = _settings(monkeypatch, database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_database_url_respeta_driver_explicito(monkeypatch: pytest.MonkeyPatch) -> None:
    """Una URL que ya trae driver no se toca (no duplica el prefijo)."""
    url = "postgresql+psycopg://u:p@host:5432/db"
    s = _settings(monkeypatch, database_url=url)
    assert s.database_url == url


def test_codigo_no_asigna_secretos_como_default() -> None:
    """Defensa de regresión: ningún secreto debe usarse como valor por DEFAULT.

    Los placeholders SÍ aparecen en `config.py` dentro del blocklist `_DEMO_SECRETS`
    (la guarda de producción), pero NUNCA como `campo: str = "<placeholder>"`. Este
    test detecta el patrón de asignación de default, no la mera presencia del string.
    """
    import inspect

    import app.core.config as config_module

    source = inspect.getsource(config_module)
    # `pub_test_demo` se excluye: es la llave PÚBLICA, sí conserva default legítimo.
    for marcador in [
        "integrity_test_secret",
        "events_test_secret",
        "cufe_demo_secret",
        "cambia-esto",
    ]:
        assert f'= "{marcador}' not in source, (
            f"Secreto usado como default en config.py: {marcador}"
        )
