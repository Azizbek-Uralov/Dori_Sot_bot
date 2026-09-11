from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings
from app.constants import Language
from app.i18n.translator import t
from bot.utils.callback_data import SubCheckCB


def _channel_url() -> str:
    channel = settings.marketing_channel_id
    if channel.startswith("@"):
        return f"https://t.me/{channel[1:]}"
    return "https://t.me/"


def subscription_keyboard(lang: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("subscribe.channel_button", lang), url=_channel_url())],
            [
                InlineKeyboardButton(
                    text=t("subscribe.check_button", lang), callback_data=SubCheckCB().pack()
                )
            ],
        ]
    )
