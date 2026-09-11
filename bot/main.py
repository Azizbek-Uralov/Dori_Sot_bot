import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.logging_conf import configure_logging
from bot.handlers import build_root_router
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.user_context import UserContextMiddleware

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    """Builds the full Dispatcher/router tree without constructing a Bot instance —
    this is what lets the bot package be imported and smoke-tested with no real
    BOT_TOKEN (see tests/test_bot_import.py)."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(UserContextMiddleware())
    dp.callback_query.middleware(UserContextMiddleware())
    dp.include_router(build_root_router())
    return dp


async def main() -> None:
    configure_logging()
    bot = Bot(token=settings.bot_token)
    dp = build_dispatcher()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Starting bot polling")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
