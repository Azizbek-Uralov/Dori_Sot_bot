from typing import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory
from app.models.admin import Admin


class NotAuthenticated(Exception):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def get_current_admin(request: Request, session: AsyncSession = Depends(get_db)) -> Admin:
    admin_id = request.session.get("admin_id")
    if admin_id is None:
        raise NotAuthenticated()
    admin = await session.get(Admin, admin_id)
    if admin is None or not admin.is_active:
        request.session.pop("admin_id", None)
        raise NotAuthenticated()
    return admin
