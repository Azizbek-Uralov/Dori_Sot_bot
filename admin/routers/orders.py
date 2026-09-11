from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from app.constants import OrderStatus
from app.services import notify_service, order_service
from app.services.order_service import InvalidStatusTransitionError

router = APIRouter(prefix="/orders", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


@router.get("")
async def list_orders(
    request: Request,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    status_enum = OrderStatus(status) if status else None
    orders = await order_service.list_orders(session, status=status_enum)
    return templates.TemplateResponse(
        request,
        "orders/list.html",
        {"orders": orders, "statuses": list(OrderStatus), "selected_status": status},
    )


@router.get("/{order_id}")
async def order_detail(order_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    order = await order_service.get_order(session, order_id)
    return templates.TemplateResponse(
        request, "orders/detail.html", {"order": order, "statuses": list(OrderStatus)}
    )


@router.post("/{order_id}/status")
async def change_order_status(
    order_id: int,
    request: Request,
    new_status: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order(session, order_id)
    if order is None:
        return RedirectResponse(url="/orders", status_code=303)
    try:
        order = await order_service.transition_status(session, order, OrderStatus(new_status))
    except InvalidStatusTransitionError:
        return RedirectResponse(url=f"/orders/{order_id}?error=invalid_transition", status_code=303)
    await notify_service.notify_customer_status_change(order, order.status)
    return RedirectResponse(url=f"/orders/{order_id}", status_code=303)
