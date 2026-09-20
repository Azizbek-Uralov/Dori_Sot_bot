"""Bootstrap the first admin login. There's no self-registration UI by design
(admins are managed from inside the admin panel once at least one exists), so
this CLI is how the very first account gets created.

Usage:
    uv run python -m scripts.create_admin --username admin --password devpass123
    uv run python -m scripts.create_admin --username admin --password devpass123 --telegram-id 123456789
"""

import argparse
import asyncio

from sqlalchemy import select

from admin.auth import hash_password
from app.db import async_session_factory
from app.models.admin import Admin


async def create_admin(username: str, password: str, full_name: str | None, telegram_id: int | None) -> None:
    async with async_session_factory() as session:
        existing = (
            await session.execute(select(Admin).where(Admin.username == username))
        ).scalar_one_or_none()
        if existing is not None:
            print(f"Admin '{username}' allaqachon mavjud.")
            return
        session.add(
            Admin(
                username=username,
                password_hash=hash_password(password),
                full_name=full_name,
                telegram_id=telegram_id,
            )
        )
        await session.commit()
        print(f"Admin '{username}' yaratildi.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin panel login")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default=None)
    parser.add_argument(
        "--telegram-id",
        type=int,
        default=None,
        help="Optional Telegram user ID, used to DM this admin about new orders",
    )
    args = parser.parse_args()
    asyncio.run(create_admin(args.username, args.password, args.full_name, args.telegram_id))


if __name__ == "__main__":
    main()
