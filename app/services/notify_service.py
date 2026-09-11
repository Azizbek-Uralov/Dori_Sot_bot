import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.utils.token import TokenValidationError

from app.config import settings
from app.constants import OrderStatus
from app.i18n.translator import t
from app.models.order import Order

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_bot_construction_failed = False


def get_bot() -> Bot | None:
    """Lazily construct a singleton Bot HTTP client, used purely for sending messages
    (no dispatcher/polling here). Never raises: a missing/placeholder BOT_TOKEN just
    disables notifications so importing/starting either process never depends on
    having a real token.
    """
    global _bot, _bot_construction_failed
    if _bot is not None:
        return _bot
    if _bot_construction_failed:
        return None
    try:
        _bot = Bot(token=settings.bot_token)
    except TokenValidationError:
        logger.warning("BOT_TOKEN is not configured or invalid; Telegram notifications are disabled")
        _bot_construction_failed = True
        return None
    return _bot


async def close_bot() -> None:
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None


def render_admin_order_text(order: Order) -> str:
    lines = [
        f"🆕 Yangi buyurtma №{order.id}",
        f"Mijoz: {order.customer_name}",
        f"Tel: {order.customer_phone}",
        "",
    ]
    for item in order.items:
        lines.append(f"— {item.product_name_uz} x{item.quantity} = {item.line_total} so'm")
    lines += [
        "",
        f"Mahsulotlar summasi: {order.items_subtotal} so'm",
        f"Yetkazib berish: {order.delivery_fee} so'm",
        f"Jami: {order.grand_total} so'm",
        f"Manzil: {order.delivery_address_text}",
    ]
    return "\n".join(lines)


async def notify_admin_group(order: Order) -> bool:
    bot = get_bot()
    if bot is None:
        return False
    try:
        await bot.send_message(settings.admin_group_chat_id, render_admin_order_text(order))
        return True
    except TelegramAPIError as exc:
        logger.warning("Failed to notify admin group for order %s: %s", order.id, exc)
        return False


async def notify_customer_status_change(order: Order, new_status: OrderStatus) -> bool:
    bot = get_bot()
    if bot is None:
        return False
    try:
        text = t(
            "notify.order_status_changed",
            order.customer_language,
            order_id=order.id,
            status=t(f"orders.status.{new_status.value}", order.customer_language),
        )
        await bot.send_message(order.user.telegram_id, text)
        return True
    except TelegramAPIError as exc:
        logger.warning("Failed to notify customer for order %s: %s", order.id, exc)
        return False
