from aiogram import F, Router
from aiogram.types import Message

from app.constants import Language
from app.i18n.translator import t
from app.models.user import User
from bot.keyboards.language import language_keyboard
from bot.keyboards.main_menu import menu_texts

router = Router(name="language")


@router.message(F.text.in_(menu_texts("menu.change_language")))
async def change_language_menu(message: Message, session, user: User) -> None:
    # Actual selection is handled by bot.handlers.start.on_language_chosen (LangCB),
    # so there is exactly one place that processes a language pick.
    await message.answer(t("language.choose", user.language or Language.UZ), reply_markup=language_keyboard())
