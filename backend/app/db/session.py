"""Engine de base de datos y dependencia de sesión para inyección en FastAPI."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

# echo=False: no logueamos SQL en consola. pool_pre_ping: reconecta si la
# conexión murió (p. ej. si el contenedor de Postgres se reinició).
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """Provee una sesión de DB por request y la cierra al terminar."""
    with Session(engine) as session:
        yield session
