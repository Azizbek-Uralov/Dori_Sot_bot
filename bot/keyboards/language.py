from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import Language
from app.i18n.translator import t
from bot.utils.callback_data import LangCB


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("language.uz_button", Language.UZ),
                    callback_data=LangCB(code=Language.UZ.value).pack(),
                ),
                InlineKeyboardButton(
                    text=t("language.ru_button", Language.RU),
                    callback_data=LangCB(code=Language.RU.value).pack(),
                ),
            ]
        ]
    )
