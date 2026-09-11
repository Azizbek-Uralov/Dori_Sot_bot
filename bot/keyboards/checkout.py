from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.constants import Language
from app.i18n.translator import localized, t
from app.models.delivery_zone import DeliveryZone
from app.services.delivery_service import compute_fee
from bot.utils.callback_data import OrderConfirmCB, ZoneCB


def phone_keyboard(lang: Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("checkout.share_contact_button", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def zones_keyboard(zones: list[DeliveryZone], items_subtotal: int, lang: Language) -> InlineKeyboardMarkup:
    rows = []
    for zone in zones:
        fee = compute_fee(zone, items_subtotal)
        fee_text = (
            t("checkout.zone_fee_free", lang)
            if fee == 0
            else t("checkout.zone_fee_amount", lang, amount=fee)
        )
        text = t("checkout.zone_fee", lang, name=localized(zone, "name", lang), fee=fee_text)
        rows.append([InlineKeyboardButton(text=text, callback_data=ZoneCB(id=zone.id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(lang: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("checkout.confirm_button", lang),
                    callback_data=OrderConfirmCB(action="confirm").pack(),
                ),
                InlineKeyboardButton(
                    text=t("checkout.cancel_button", lang),
                    callback_data=OrderConfirmCB(action="cancel").pack(),
                ),
            ]
        ]
    )
