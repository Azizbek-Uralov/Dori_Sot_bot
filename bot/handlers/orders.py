from aiogram import F, Router
from aiogram.types import Message

from app.i18n.translator import t
from app.models.user import User
from app.services import order_service
from bot.keyboards.main_menu import menu_texts

router = Router(name="orders")

# Read-only by design: no cancel callback/handler is registered here.
# Order cancellation is only reachable through the admin panel
# (admin/routers/orders.py -> POST /orders/{id}/status).


@router.message(F.text.in_(menu_texts("menu.my_orders")))
async def my_orders(message: Message, session, user: User) -> None:
    orders = await order_service.list_orders_for_user(session, user.id)
    lang = user.language
    if not orders:
        await message.answer(t("orders.empty", lang))
        return
    lines = [t("orders.title", lang)]
    for order in orders:
        status_label = t(f"orders.status.{order.status.value}", lang)
        lines.append(
            t(
                "orders.item_line",
                lang,
                order_id=order.id,
                date=order.created_at.strftime("%Y-%m-%d"),
                total=order.grand_total,
                status=status_label,
            )
        )
    await message.answer("\n".join(lines))
