from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import Language
from app.i18n.translator import localized, t
from app.services.cart_service import CartLine
from bot.utils.callback_data import CartItemCB

NOOP = "noop"
PLACE_ORDER = "cart_place_order"


def cart_keyboard(lines: list[CartLine], lang: Language) -> InlineKeyboardMarkup:
    rows = []
    for line in lines:
        name = localized(line.product, "name", lang)
        rows.append(
            [
                InlineKeyboardButton(
                    text="➖",
                    callback_data=CartItemCB(product_id=line.product.id, action="dec").pack(),
                ),
                InlineKeyboardButton(text=f"{name} x{line.quantity}", callback_data=NOOP),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=CartItemCB(product_id=line.product.id, action="inc").pack(),
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=CartItemCB(product_id=line.product.id, action="remove").pack(),
                ),
            ]
        )
    if lines:
        rows.append([InlineKeyboardButton(text=t("cart.place_order_button", lang), callback_data=PLACE_ORDER)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
