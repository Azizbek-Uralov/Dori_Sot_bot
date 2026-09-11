from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import Language
from app.i18n.translator import localized, t
from app.models.category import Category
from app.models.product import Product
from bot.utils.callback_data import AddToCartCB, CategoryCB, ProductCB

BACK_TO_CATEGORIES = "catalog_back_categories"


def categories_keyboard(categories: list[Category], lang: Language) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=localized(c, "name", lang), callback_data=CategoryCB(id=c.id).pack())]
        for c in categories
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_keyboard(products: list[Product], lang: Language) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=localized(p, "name", lang), callback_data=ProductCB(id=p.id).pack())]
        for p in products
    ]
    rows.append(
        [InlineKeyboardButton(text=t("catalog.back_to_categories", lang), callback_data=BACK_TO_CATEGORIES)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_keyboard(product: Product, lang: Language) -> InlineKeyboardMarkup:
    rows = []
    if product.is_purchasable:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("catalog.add_to_cart", lang),
                    callback_data=AddToCartCB(product_id=product.id).pack(),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("catalog.back_to_products", lang),
                callback_data=CategoryCB(id=product.category_id).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
