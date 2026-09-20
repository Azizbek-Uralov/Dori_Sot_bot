from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.constants import MIN_ORDER_TOTAL, Language
from app.i18n.translator import t
from app.models.user import User
from app.services import cart_service, delivery_service, notify_service, order_service
from app.services.order_service import InsufficientStockError, MinOrderNotMetError
from bot.keyboards.cart import PLACE_ORDER
from bot.keyboards.checkout import confirm_keyboard, phone_keyboard, zones_keyboard
from bot.keyboards.main_menu import main_menu_keyboard
from bot.states.checkout import CheckoutStates
from bot.utils.callback_data import OrderConfirmCB, ZoneCB
from bot.utils.phone import PHONE_RE

router = Router(name="checkout")


def _full_name_prompt(lang: Language) -> str:
    """Always the same static prompt with a made-up example name, regardless
    of the user's own saved full_name — that must never be echoed back."""
    return t("checkout.ask_full_name", lang)


@router.callback_query(F.data == PLACE_ORDER)
async def place_order_entry(callback: CallbackQuery, state: FSMContext, session, user: User) -> None:
    await callback.answer()
    if not callback.message:
        return
    summary = await cart_service.get_summary(session, user)
    lang = user.language
    if summary.subtotal < MIN_ORDER_TOTAL:
        await callback.message.answer(
            t(
                "checkout.min_order_not_met",
                lang,
                min_total=MIN_ORDER_TOTAL,
                current_total=summary.subtotal,
                shortfall=MIN_ORDER_TOTAL - summary.subtotal,
            )
        )
        return
    await state.update_data(items_subtotal=summary.subtotal)
    await state.set_state(CheckoutStates.waiting_full_name)
    await callback.message.answer(_full_name_prompt(lang))


@router.message(CheckoutStates.waiting_full_name, F.text)
async def receive_full_name(message: Message, state: FSMContext, session, user: User) -> None:
    full_name = (message.text or "").strip()
    if not full_name:
        await message.answer(_full_name_prompt(user.language))
        return
    await state.update_data(full_name=full_name)
    await state.set_state(CheckoutStates.waiting_phone)
    await message.answer(t("checkout.ask_phone", user.language), reply_markup=phone_keyboard(user.language))


@router.message(CheckoutStates.waiting_phone, F.contact)
async def receive_phone_contact(message: Message, state: FSMContext, session, user: User) -> None:
    await _save_phone_and_advance(message, state, session, user, message.contact.phone_number)


@router.message(CheckoutStates.waiting_phone, F.text)
async def receive_phone_text(message: Message, state: FSMContext, session, user: User) -> None:
    phone = (message.text or "").strip()
    if not PHONE_RE.match(phone):
        await message.answer(t("checkout.invalid_phone", user.language))
        return
    await _save_phone_and_advance(message, state, session, user, phone)


async def _save_phone_and_advance(message: Message, state: FSMContext, session, user: User, phone: str) -> None:
    await state.update_data(phone=phone)
    lang = user.language
    zones = await delivery_service.list_zones(session)
    if not zones:
        await message.answer(t("error.generic", lang), reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return
    data = await state.get_data()
    await state.set_state(CheckoutStates.waiting_zone)
    await message.answer(t("checkout.phone_received", lang), reply_markup=ReplyKeyboardRemove())
    await message.answer(
        t("checkout.ask_zone", lang), reply_markup=zones_keyboard(zones, data["items_subtotal"], lang)
    )


@router.callback_query(CheckoutStates.waiting_zone, ZoneCB.filter())
async def receive_zone(
    callback: CallbackQuery, callback_data: ZoneCB, state: FSMContext, session, user: User
) -> None:
    await callback.answer()
    if not callback.message:
        return
    zone = await delivery_service.get_zone(session, callback_data.id)
    if zone is None:
        return
    await state.update_data(zone_id=zone.id)
    await state.set_state(CheckoutStates.waiting_address)
    await callback.message.answer(t("checkout.ask_address", user.language))


@router.message(CheckoutStates.waiting_address, F.text)
async def receive_address(message: Message, state: FSMContext, session, user: User) -> None:
    address = (message.text or "").strip()
    if not address:
        await message.answer(t("checkout.ask_address", user.language))
        return
    await state.update_data(address=address)
    data = await state.get_data()
    zone = await delivery_service.get_zone(session, data["zone_id"])
    if zone is None:
        await message.answer(t("error.generic", user.language))
        await state.clear()
        return
    lang = user.language
    fee = delivery_service.compute_fee(zone, data["items_subtotal"])
    grand_total = data["items_subtotal"] + fee
    summary_text = "\n".join(
        [
            t("checkout.confirm_title", lang),
            t("checkout.confirm_items_subtotal", lang, amount=data["items_subtotal"]),
            t("checkout.confirm_delivery_fee", lang, amount=fee),
            t("checkout.confirm_grand_total", lang, amount=grand_total),
            t("checkout.confirm_address", lang, address=address),
        ]
    )
    await state.set_state(CheckoutStates.waiting_confirm)
    await message.answer(summary_text, reply_markup=confirm_keyboard(lang))


@router.callback_query(CheckoutStates.waiting_confirm, OrderConfirmCB.filter())
async def confirm_order(
    callback: CallbackQuery, callback_data: OrderConfirmCB, state: FSMContext, session, user: User
) -> None:
    await callback.answer()
    if not callback.message:
        return
    lang = user.language

    if callback_data.action == "cancel":
        await state.clear()
        await callback.message.answer(t("checkout.cancelled", lang), reply_markup=main_menu_keyboard(lang))
        return

    data = await state.get_data()
    zone = await delivery_service.get_zone(session, data["zone_id"])
    if zone is None:
        await callback.message.answer(t("error.generic", lang))
        await state.clear()
        return

    try:
        order = await order_service.create_order(
            session,
            user,
            full_name=data["full_name"],
            phone=data["phone"],
            zone=zone,
            delivery_address_text=data["address"],
            customer_language=lang,
        )
    except MinOrderNotMetError as exc:
        await callback.message.answer(
            t(
                "checkout.min_order_not_met",
                lang,
                min_total=exc.min_total,
                current_total=exc.current_total,
                shortfall=exc.shortfall,
            )
        )
        await state.clear()
        return
    except InsufficientStockError as exc:
        name = exc.product_name_uz if lang == Language.UZ else exc.product_name_ru
        await callback.message.answer(t("checkout.stock_changed", lang, name=name))
        await state.clear()
        return

    await state.clear()
    await callback.message.answer(
        t("checkout.order_created", lang, order_id=order.id), reply_markup=main_menu_keyboard(lang)
    )

    order_with_relations = await order_service.get_order(session, order.id)
    if order_with_relations is not None:
        sent = await notify_service.notify_admin_group(order_with_relations)
        # the group chat is the shared inbox; admins who put their Telegram ID
        # in the panel also get the order as a private message
        dm_count = await notify_service.notify_admins_direct(session, order_with_relations)
        if sent or dm_count:
            order_with_relations.admin_notified_at = datetime.now(timezone.utc)
            await session.commit()
