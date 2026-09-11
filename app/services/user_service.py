from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import Language
from app.models.user import User


async def get_or_create_user(session: AsyncSession, telegram_id: int, full_name: str | None = None) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user, attribute_names=["created_at", "updated_at"])
    return user


async def set_language(session: AsyncSession, user: User, language: Language) -> None:
    user.language = language
    await session.commit()
    await session.refresh(user, attribute_names=["updated_at"])
