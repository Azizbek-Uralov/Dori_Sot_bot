from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.services.user_service import get_or_create_user


class UserContextMiddleware(BaseMiddleware):
    """Loads (or creates) the User row for the current Telegram sender and injects
    it into handler data as `user`, so every downstream handler/middleware can rely
    on it being present without a separate DB round trip."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        tg_user = data.get("event_from_user")
        if session is not None and tg_user is not None:
            data["user"] = await get_or_create_user(session, tg_user.id, tg_user.full_name)
        return await handler(event, data)
