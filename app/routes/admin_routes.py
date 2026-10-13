from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.controllers.admin_controller import (
    get_dashboard_stats,
    get_sales_analytics,
)

from app.middleware.auth import JWTBearer, get_current_admin


router = APIRouter()


# ============================================================
# DASHBOARD
# ============================================================

@router.get(
    "/dashboard/stats",
    tags=["Admin"],
    dependencies=[Depends(JWTBearer())],
)
async def get_dashboard(
    admin_id: str = Depends(get_current_admin),
):
    """
    Get admin dashboard statistics.
    """
    return await get_dashboard_stats()


# ============================================================
# SALES ANALYTICS
# ============================================================

@router.get(
    "/analytics/sales",
    tags=["Admin"],
    dependencies=[Depends(JWTBearer())],
)
async def get_sales_analytics_route(
    period: str = Query(
        "monthly",
        regex="^(daily|weekly|monthly)$",
        description="Analytics period",
    ),
    year: Optional[int] = Query(
        None,
        description="Year for analytics",
    ),
    month: Optional[int] = Query(
        None,
        ge=1,
        le=12,
        description="Month for analytics",
    ),
    admin_id: str = Depends(get_current_admin),
):
    """
    Get sales analytics (admin only).
    """
    return await get_sales_analytics(
        period,
        year,
        month,
    )