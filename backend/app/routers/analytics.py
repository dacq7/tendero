"""Endpoints de analítica (agregaciones en backend). SOLO admin.

Parámetros comunes: `desde`/`hasta` (date, por defecto últimos 30 días, `hasta`
inclusivo) y `granularidad` (dia/semana/mes/ano).
"""

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app.core.deps import require_role
from app.db.session import get_session
from app.models.user import UserRole
from app.routers._errors import http_error
from app.schemas.analytics import (
    AnalyticsSummary,
    ByCashierRow,
    ByMethodRow,
    Granularidad,
    InventoryStats,
    PeakHourCell,
    TimeSeriesPoint,
    TopCategory,
    TopProduct,
)
from app.services import analytics_service
from app.services.analytics_errors import AnalyticsError

router = APIRouter(
    prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_role(UserRole.admin))]
)


def _rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hasta = hasta or date.today()
    desde = desde or (hasta - timedelta(days=29))
    return desde, hasta


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    desde: date | None = None,
    hasta: date | None = None,
    comparar: bool = True,
    session: Session = Depends(get_session),
) -> AnalyticsSummary:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.summary(session, d, h, comparar=comparar)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/timeseries", response_model=list[TimeSeriesPoint])
def get_timeseries(
    desde: date | None = None,
    hasta: date | None = None,
    granularidad: Granularidad = Granularidad.dia,
    session: Session = Depends(get_session),
) -> list[TimeSeriesPoint]:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.timeseries(session, d, h, granularidad)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/top-products", response_model=list[TopProduct])
def get_top_products(
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> list[TopProduct]:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.top_products(session, d, h, limit)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/top-categories", response_model=list[TopCategory])
def get_top_categories(
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> list[TopCategory]:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.top_categories(session, d, h, limit)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/by-method", response_model=list[ByMethodRow])
def get_by_method(
    desde: date | None = None,
    hasta: date | None = None,
    session: Session = Depends(get_session),
) -> list[ByMethodRow]:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.by_method(session, d, h)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/by-cashier", response_model=list[ByCashierRow])
def get_by_cashier(
    desde: date | None = None,
    hasta: date | None = None,
    session: Session = Depends(get_session),
) -> list[ByCashierRow]:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.by_cashier(session, d, h)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/peak-hours", response_model=list[PeakHourCell])
def get_peak_hours(
    desde: date | None = None,
    hasta: date | None = None,
    session: Session = Depends(get_session),
) -> list[PeakHourCell]:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.peak_hours(session, d, h)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/inventory", response_model=InventoryStats)
def get_inventory(
    desde: date | None = None,
    hasta: date | None = None,
    session: Session = Depends(get_session),
) -> InventoryStats:
    d, h = _rango(desde, hasta)
    try:
        return analytics_service.inventory(session, d, h)
    except AnalyticsError as exc:
        raise http_error(exc) from exc


@router.get("/export.csv")
def export_csv(
    dataset: Literal["summary", "timeseries", "top-products"] = "summary",
    desde: date | None = None,
    hasta: date | None = None,
    granularidad: Granularidad = Granularidad.dia,
    session: Session = Depends(get_session),
) -> Response:
    d, h = _rango(desde, hasta)
    try:
        contenido = analytics_service.export_csv(session, dataset, d, h, granularidad)
    except AnalyticsError as exc:
        raise http_error(exc) from exc
    return Response(
        content=contenido,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="tendero-{dataset}.csv"'},
    )
