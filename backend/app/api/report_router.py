"""Reporting endpoints: aggregate production KPIs over a time window.

The heavy lifting lives in :class:`~app.services.ReportService`; the router only
parses query parameters and serialises the computed summary.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from app.api.dependencies import ReportServiceDep
from app.schemas.entities import ReportSummary
from app.utils.time_utils import utc_now


def _default_window() -> tuple[datetime, datetime]:
    """Return the last 24 hours as a ``(start, end)`` default window."""
    end = utc_now()
    return end - timedelta(days=1), end


router = APIRouter(prefix="/report", tags=["report"])


@router.get(
    "",
    response_model=ReportSummary,
    summary="Production KPI summary over a window",
)
async def report_summary(
    service: ReportServiceDep,
    start: Optional[datetime] = Query(None, description="Window start (UTC)."),
    end: Optional[datetime] = Query(None, description="Window end (UTC)."),
    machine_id: Optional[int] = Query(None, description="Filter by machine id."),
) -> ReportSummary:
    """Compute PASS/FAIL/yield/defect-rate/avg-time for the window.

    When ``start``/``end`` are omitted, the last 24 hours are used.
    """
    if start is None or end is None:
        default_start, default_end = _default_window()
        start = start or default_start
        end = end or default_end

    summary = service.summary(start, end, machine_id=machine_id)
    return ReportSummary(**summary)


__all__ = ["router"]
