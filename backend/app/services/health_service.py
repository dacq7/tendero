"""Lógica de negocio para el chequeo de salud. Aquí vive la verificación real."""

from sqlalchemy import text
from sqlmodel import Session


def check_database(session: Session) -> bool:
    """Ejecuta un SELECT 1 contra Postgres. True si la DB responde."""
    result = session.execute(text("SELECT 1")).first()
    return result is not None
