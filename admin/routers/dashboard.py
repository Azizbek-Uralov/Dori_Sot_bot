from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from app.models.admin import Admin
from app.services import order_service, stats_service

router = APIRouter(dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    totals = await stats_service.sales_totals(session)
    recent_orders = await order_service.list_orders(session)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"admin": admin, "totals": totals, "recent_orders": recent_orders[:10]},
    )
