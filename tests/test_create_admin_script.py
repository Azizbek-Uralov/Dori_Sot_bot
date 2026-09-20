"""scripts/create_admin.py talks to the production async_session_factory
directly, so each test rebinds that module-level factory to the shared test
engine before calling it — otherwise it would reach for the real database.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.admin import Admin
from scripts import create_admin


async def test_create_admin_with_telegram_id(test_engine, db_session, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(create_admin, "async_session_factory", session_factory)

    await create_admin.create_admin("cli_admin", "devpass123", "CLI Admin", 123456789)

    admin = (
        await db_session.execute(select(Admin).where(Admin.username == "cli_admin"))
    ).scalar_one()
    assert admin.telegram_id == 123456789
    assert admin.full_name == "CLI Admin"


async def test_create_admin_without_telegram_id_defaults_to_null(test_engine, db_session, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(create_admin, "async_session_factory", session_factory)

    await create_admin.create_admin("cli_admin2", "devpass123", None, None)

    admin = (
        await db_session.execute(select(Admin).where(Admin.username == "cli_admin2"))
    ).scalar_one()
    assert admin.telegram_id is None


async def test_create_admin_skips_existing_username(test_engine, db_session, monkeypatch, capsys):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(create_admin, "async_session_factory", session_factory)

    await create_admin.create_admin("dup", "devpass123", None, 111)
    await create_admin.create_admin("dup", "devpass123", None, 222)

    admins = (
        await db_session.execute(select(Admin).where(Admin.username == "dup"))
    ).scalars().all()
    assert len(admins) == 1
    assert admins[0].telegram_id == 111


def test_main_parses_and_forwards_telegram_id_argument(monkeypatch):
    calls = []

    async def fake_create_admin(username, password, full_name, telegram_id):
        calls.append((username, password, full_name, telegram_id))

    monkeypatch.setattr(create_admin, "create_admin", fake_create_admin)
    monkeypatch.setattr(
        "sys.argv",
        ["create_admin.py", "--username", "cli", "--password", "pw", "--telegram-id", "42"],
    )

    create_admin.main()

    assert calls == [("cli", "pw", None, 42)]


def test_main_defaults_telegram_id_to_none_when_omitted(monkeypatch):
    calls = []

    async def fake_create_admin(username, password, full_name, telegram_id):
        calls.append((username, password, full_name, telegram_id))

    monkeypatch.setattr(create_admin, "create_admin", fake_create_admin)
    monkeypatch.setattr("sys.argv", ["create_admin.py", "--username", "cli", "--password", "pw"])

    create_admin.main()

    assert calls == [("cli", "pw", None, None)]
