"""Fixtures de pruebas: base de datos de test aislada (tendero_test).

Estrategia (decidida en sub-fase 0.7):
- Base SEPARADA `tendero_test` en el mismo Postgres de Docker (puerto 5436).
- El esquema se construye con las MIGRACIONES REALES (`alembic upgrade head`),
  no con `create_all`, para ejercitarlas de verdad.
- La URL sale de `TEST_DATABASE_URL`; si no, se deriva de `DATABASE_URL`
  añadiendo el sufijo `_test` al nombre de la base.
- Se crea/limpia la base una vez por sesión de test. Guarda de seguridad:
  jamás se corre contra la base de desarrollo.
"""

import os
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlmodel import Session

from alembic import command
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_session
from app.main import app
from app.models.user import User, UserRole
from app.repositories import user_repository

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Credenciales del admin sembrado para los tests (solo entorno de pruebas).
ADMIN_EMAIL = "admin@test.co"
ADMIN_PASSWORD = "Test1234!"


def _test_database_url() -> URL:
    """URL de la base de test: explícita por env o derivada con sufijo `_test`.

    Se trabaja con objetos `URL` (no strings) porque `str(url)` enmascara la
    contraseña como `***`; un round-trip a texto rompería la autenticación.
    """
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return make_url(explicit)
    dev = make_url(settings.database_url)
    return dev.set(database=f"{dev.database}_test")


def _maintenance_engine(url: URL) -> Engine:
    """Engine en autocommit contra la base de mantenimiento `postgres`.

    CREATE/DROP DATABASE no pueden ir dentro de una transacción.
    """
    admin_url = url.set(database="postgres")
    return create_engine(admin_url, isolation_level="AUTOCOMMIT")


def _drop_database(conn, dbname: str) -> None:
    """Cierra conexiones colgadas y elimina la base si existe."""
    conn.execute(
        text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = :db AND pid <> pg_backend_pid()"
        ),
        {"db": dbname},
    )
    conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}"'))


@pytest.fixture(scope="session")
def _engine() -> Engine:
    """Crea `tendero_test`, le aplica las migraciones y entrega un engine.

    Al terminar la sesión, elimina la base de test.
    """
    test_url = _test_database_url()
    dev_url = make_url(settings.database_url)

    # Guardas de seguridad: la fixture hace DROP/CREATE DATABASE (destructivo),
    # así que blindamos el destino. Nunca la base de desarrollo y el nombre
    # SIEMPRE debe terminar en '_test', venga de env var o derivado.
    assert test_url.database != dev_url.database, (
        f"La base de test no puede ser la misma que la de desarrollo ({dev_url.database!r})."
    )
    assert test_url.database.endswith("_test"), (
        "Por seguridad, la base de test SIEMPRE debe terminar en '_test'."
    )

    dbname = test_url.database

    # (Re)crear la base desde cero para una sesión limpia.
    admin = _maintenance_engine(test_url)
    with admin.connect() as conn:
        _drop_database(conn, dbname)
        conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    admin.dispose()

    # Apuntar Alembic a la base de test (env.py respeta esta URL si está fijada)
    # y construir el esquema con las migraciones reales. No mutamos el singleton
    # `settings`: la URL vive solo en esta Config local.
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_url.render_as_string(hide_password=False))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_url, pool_pre_ping=True)
    yield engine
    engine.dispose()

    # Limpieza: eliminar la base de test.
    admin = _maintenance_engine(test_url)
    with admin.connect() as conn:
        _drop_database(conn, dbname)
    admin.dispose()


@pytest.fixture(autouse=True)
def _truncate(_engine: Engine):
    """Vacía las tablas tras cada test (aislamiento). CASCADE cubre las FKs."""
    yield
    with _engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE sale_items, invoices, sales, cash_register_sessions, "
                "invoice_sequences, inventory_movements, products, suppliers, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        # invoice_sequences se truncó: re-sembrar la serie POS (como la migración).
        conn.execute(text("INSERT INTO invoice_sequences (serie, last_numero) VALUES ('POS', 0)"))
        conn.commit()


@pytest.fixture
def session(_engine: Engine) -> Session:
    with Session(_engine) as s:
        yield s


@pytest.fixture
def client(_engine: Engine) -> TestClient:
    """TestClient con la dependencia de sesión apuntando a la base de test."""

    def _override() -> Session:
        with Session(_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(session: Session) -> User:
    """Admin sembrado con hash argon2 real, listo para autenticar."""
    return user_repository.create(
        session,
        email=ADMIN_EMAIL,
        full_name="Admin Test",
        hashed_password=hash_password(ADMIN_PASSWORD),
        role=UserRole.admin,
    )


# Credenciales del cajero sembrado para los tests (solo entorno de pruebas).
CAJERO_EMAIL = "cajero@test.co"
CAJERO_PASSWORD = "Caja1234!"


@pytest.fixture
def cajero_user(session: Session) -> User:
    """Cajero sembrado: rol de solo-consulta en inventario."""
    return user_repository.create(
        session,
        email=CAJERO_EMAIL,
        full_name="Cajero Test",
        hashed_password=hash_password(CAJERO_PASSWORD),
        role=UserRole.cajero,
    )


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    """Hace login y devuelve el header Authorization con el access token."""
    res = client.post("/auth/login", json={"email": email, "password": password})
    res.raise_for_status()
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient, admin_user: User) -> dict[str, str]:
    return auth_headers(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def cajero_headers(client: TestClient, cajero_user: User) -> dict[str, str]:
    return auth_headers(client, CAJERO_EMAIL, CAJERO_PASSWORD)
