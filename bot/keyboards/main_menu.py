from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.constants import Language
from app.i18n.translator import t


def menu_texts(key: str) -> list[str]:
    return [t(key, Language.UZ), t(key, Language.RU)]


def main_menu_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu.catalog", lang)), KeyboardButton(text=t("menu.cart", lang))],
            [
                KeyboardButton(text=t("menu.my_orders", lang)),
                KeyboardButton(text=t("menu.help", lang)),
            ],
            [KeyboardButton(text=t("menu.change_language", lang))],
        ],
        resize_keyboard=True,
    )
