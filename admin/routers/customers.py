from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from app.services import customer_service, order_service

router = APIRouter(prefix="/customers", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


@router.get("")
async def list_customers(request: Request, session: AsyncSession = Depends(get_db)):
    customers = await customer_service.list_customers_with_stats(session)
    return templates.TemplateResponse(request, "customers/list.html", {"customers": customers})


@router.get("/{user_id}")
async def customer_detail(user_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    customer = await customer_service.get_customer(session, user_id)
    orders = await order_service.list_orders_for_user(session, user_id)
    return templates.TemplateResponse(
        request, "customers/detail.html", {"customer": customer, "orders": orders}
    )
