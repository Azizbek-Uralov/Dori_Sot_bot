from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from app.services import stats_service

router = APIRouter(prefix="/stats", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


@router.get("")
async def stats_page(request: Request, session: AsyncSession = Depends(get_db)):
    totals = await stats_service.sales_totals(session)
    best_selling = await stats_service.best_selling_products(session)
    status_counts = await stats_service.orders_by_status(session)
    return templates.TemplateResponse(
        request,
        "stats.html",
        {"totals": totals, "best_selling": best_selling, "status_counts": status_counts},
    )
