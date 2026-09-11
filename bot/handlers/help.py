from aiogram import F, Router
from aiogram.types import Message

from app.config import settings
from app.i18n.translator import t
from app.models.user import User
from bot.keyboards.main_menu import menu_texts

router = Router(name="help")


@router.message(F.text.in_(menu_texts("menu.help")))
async def help_handler(message: Message, session, user: User) -> None:
    await message.answer(t("help.text", user.language, contact=settings.support_contact))
