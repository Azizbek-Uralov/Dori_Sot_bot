from typing import Callable

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.constants import Language
from app.i18n.translator import t
from app.models.user import User
from app.services.user_service import set_language
from bot.keyboards.language import language_keyboard
from bot.keyboards.main_menu import main_menu_keyboard
from bot.keyboards.subscription import subscription_keyboard
from bot.utils.callback_data import LangCB, SubCheckCB
from bot.utils.subscription import check_subscription

router = Router(name="start")


async def _greet_and_gate(answer: Callable, bot, user: User, display_name: str | None) -> None:
    lang = user.language
    await answer(t("start.welcome", lang, name=user.full_name or display_name or ""))
    if not await check_subscription(bot, user.telegram_id):
        await answer(t("subscribe.prompt", lang), reply_markup=subscription_keyboard(lang))
        return
    await answer(t("menu.prompt", lang), reply_markup=main_menu_keyboard(lang))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session, user: User) -> None:
    await state.clear()
    if user.language is None:
        await message.answer(t("language.choose", Language.UZ), reply_markup=language_keyboard())
        return
    await _greet_and_gate(message.answer, message.bot, user, message.from_user.full_name)


@router.callback_query(LangCB.filter())
async def on_language_chosen(callback: CallbackQuery, callback_data: LangCB, session, user: User) -> None:
    lang = Language(callback_data.code)
    await set_language(session, user, lang)
    await callback.answer(t("language.changed", lang))
    if callback.message:
        await callback.message.delete()
        await _greet_and_gate(callback.message.answer, callback.bot, user, callback.from_user.full_name)


@router.callback_query(SubCheckCB.filter())
async def recheck_subscription(callback: CallbackQuery, session, user: User) -> None:
    lang = user.language or Language.UZ
    if not await check_subscription(callback.bot, user.telegram_id):
        await callback.answer(t("subscribe.not_subscribed", lang), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.delete()
        await callback.message.answer(t("menu.prompt", lang), reply_markup=main_menu_keyboard(lang))
