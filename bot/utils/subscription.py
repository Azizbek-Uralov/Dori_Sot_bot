import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.config import settings

logger = logging.getLogger(__name__)

_ALLOWED_STATUSES = {"member", "administrator", "creator"}


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Fails closed: any API error (bot not in channel, wrong id, etc.) is treated
    as not-subscribed and logged, rather than silently letting the user through."""
    try:
        member = await bot.get_chat_member(chat_id=settings.marketing_channel_id, user_id=user_id)
    except TelegramAPIError as exc:
        logger.warning("Subscription check failed for user %s: %s", user_id, exc)
        return False
    return member.status in _ALLOWED_STATUSES
