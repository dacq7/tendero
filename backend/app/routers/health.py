"""Endpoint de salud. El router solo orquesta; la verificación vive en el service."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.services.health_service import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    db_ok = check_database(session)
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "tendero-backend",
        "database": "up" if db_ok else "down",
    }
