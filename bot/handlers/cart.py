from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from app.i18n.translator import localized, t
from app.models.user import User
from app.services import cart_service
from bot.keyboards.cart import NOOP, cart_keyboard
from bot.keyboards.main_menu import menu_texts
from bot.utils.callback_data import CartItemCB

router = Router(name="cart")


async def _render_cart(session, user: User) -> tuple[str, object | None]:
    summary = await cart_service.get_summary(session, user)
    lang = user.language
    if not summary.lines:
        return t("cart.empty", lang), None
    lines_text = [t("cart.title", lang)]
    for line in summary.lines:
        lines_text.append(
            t(
                "cart.item_line",
                lang,
                name=localized(line.product, "name", lang),
                qty=line.quantity,
                price=line.product.price,
                line_total=line.line_total,
            )
        )
    lines_text.append(t("cart.total", lang, total=summary.subtotal))
    return "\n".join(lines_text), cart_keyboard(summary.lines, lang)


@router.message(F.text.in_(menu_texts("menu.cart")))
async def open_cart(message: Message, session, user: User) -> None:
    text, kb = await _render_cart(session, user)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == NOOP)
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(CartItemCB.filter())
async def modify_cart_item(
    callback: CallbackQuery, callback_data: CartItemCB, session, user: User
) -> None:
    if callback_data.action == "inc":
        await cart_service.add_item(session, user, callback_data.product_id, 1)
    elif callback_data.action == "dec":
        summary = await cart_service.get_summary(session, user)
        current = next(
            (line.quantity for line in summary.lines if line.product.id == callback_data.product_id), 0
        )
        await cart_service.set_quantity(session, user, callback_data.product_id, current - 1)
    elif callback_data.action == "remove":
        await cart_service.remove_item(session, user, callback_data.product_id)

    await callback.answer()
    if not callback.message:
        return
    text, kb = await _render_cart(session, user)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb)
