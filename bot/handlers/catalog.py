from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.i18n.translator import localized, t
from app.models.user import User
from app.services import cart_service, catalog_service
from bot.keyboards.catalog import (
    BACK_TO_CATEGORIES,
    categories_keyboard,
    product_detail_keyboard,
    products_keyboard,
)
from bot.keyboards.main_menu import menu_texts
from bot.utils.callback_data import AddToCartCB, CategoryCB, ProductCB

router = Router(name="catalog")


@router.message(F.text.in_(menu_texts("menu.catalog")))
async def open_catalog(message: Message, session, user: User) -> None:
    await _send_categories(message.answer, session, user)


@router.callback_query(F.data == BACK_TO_CATEGORIES)
async def back_to_categories(callback: CallbackQuery, session, user: User) -> None:
    await callback.answer()
    if callback.message:
        await _send_categories(callback.message.answer, session, user)


async def _send_categories(answer, session, user: User) -> None:
    categories = await catalog_service.list_categories(session)
    if not categories:
        await answer(t("catalog.no_categories", user.language))
        return
    await answer(t("catalog.choose_category", user.language), reply_markup=categories_keyboard(categories, user.language))


@router.callback_query(CategoryCB.filter())
async def show_products(callback: CallbackQuery, callback_data: CategoryCB, session, user: User) -> None:
    await callback.answer()
    if not callback.message:
        return
    products = await catalog_service.list_products(session, callback_data.id, active_only=True)
    lang = user.language
    if not products:
        await callback.message.answer(t("catalog.no_products", lang))
        return
    await callback.message.answer(t("catalog.choose_product", lang), reply_markup=products_keyboard(products, lang))


@router.callback_query(ProductCB.filter())
async def show_product_detail(callback: CallbackQuery, callback_data: ProductCB, session, user: User) -> None:
    await callback.answer()
    if not callback.message:
        return
    product = await catalog_service.get_product(session, callback_data.id)
    if product is None:
        return
    lang = user.language
    name = localized(product, "name", lang)
    description = localized(product, "description", lang) or ""
    availability = "" if product.is_purchasable else f"\n{t('catalog.out_of_stock', lang)}"
    text = f"{name}\n{description}\n{t('catalog.price', lang, price=product.price)}{availability}"
    kb = product_detail_keyboard(product, lang)
    if product.image_path:
        try:
            await callback.message.answer_photo(FSInputFile(product.image_path), caption=text, reply_markup=kb)
            return
        except (TelegramBadRequest, FileNotFoundError, OSError):
            pass
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(AddToCartCB.filter())
async def add_to_cart(callback: CallbackQuery, callback_data: AddToCartCB, session, user: User) -> None:
    product = await catalog_service.get_product(session, callback_data.product_id)
    if product is None or not product.is_purchasable:
        await callback.answer()
        return
    await cart_service.add_item(session, user, product.id, 1)
    lang = user.language
    await callback.answer(t("catalog.added_to_cart", lang, name=localized(product, "name", lang), qty=1))
