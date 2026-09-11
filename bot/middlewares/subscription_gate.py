from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.constants import Language
from app.i18n.translator import t
from bot.keyboards.language import language_keyboard
from bot.keyboards.subscription import subscription_keyboard
from bot.utils.subscription import check_subscription


class SubscriptionMiddleware(BaseMiddleware):
    """Attached only to the gated_router (catalog/cart/checkout/orders/help) — start
    and language-selection handlers stay ungated so a user can even get through this
    gate in the first place."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("user")
        bot = data.get("bot")
        if user is None or bot is None:
            return await handler(event, data)

        if user.language is None:
            await _reply(event, t("language.choose", Language.UZ), language_keyboard())
            return None

        if not await check_subscription(bot, user.telegram_id):
            await _reply(event, t("subscribe.prompt", user.language), subscription_keyboard(user.language))
            return None

        return await handler(event, data)


async def _reply(event: TelegramObject, text: str, reply_markup) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message:
            await event.message.answer(text, reply_markup=reply_markup)
    elif isinstance(event, Message):
        await event.answer(text, reply_markup=reply_markup)
