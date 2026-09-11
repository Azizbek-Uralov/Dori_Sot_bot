import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import admin.deps as admin_deps
from admin.auth import hash_password
from admin.main import create_app
from app import models  # noqa: F401  (registers every model on Base.metadata)
from app.config import settings
from app.constants import Language
from app.db import Base
from app.models.admin import Admin
from app.models.category import Category
from app.models.delivery_zone import DeliveryZone
from app.models.product import Product
from app.models.user import User


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(settings.test_database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))


async def make_user(session: AsyncSession, *, telegram_id: int = 1, language=Language.UZ, **kwargs) -> User:
    user = User(telegram_id=telegram_id, language=language, **kwargs)
    session.add(user)
    await session.flush()
    return user


async def make_category(session: AsyncSession, *, name_uz: str = "Vitaminlar", name_ru: str = "Витамины", **kwargs) -> Category:
    category = Category(name_uz=name_uz, name_ru=name_ru, **kwargs)
    session.add(category)
    await session.flush()
    return category


async def make_product(
    session: AsyncSession,
    *,
    category: Category,
    name_uz: str = "Test mahsulot",
    name_ru: str = "Тестовый товар",
    price: int = 20000,
    stock_quantity: int = 10,
    is_active: bool = True,
    **kwargs,
) -> Product:
    product = Product(
        category_id=category.id,
        name_uz=name_uz,
        name_ru=name_ru,
        price=price,
        stock_quantity=stock_quantity,
        is_active=is_active,
        **kwargs,
    )
    session.add(product)
    await session.flush()
    return product


async def make_zone(
    session: AsyncSession,
    *,
    name_uz: str = "Chilonzor",
    name_ru: str = "Чиланзар",
    delivery_price: int = 15000,
    free_delivery_threshold: int | None = None,
    **kwargs,
) -> DeliveryZone:
    zone = DeliveryZone(
        name_uz=name_uz,
        name_ru=name_ru,
        delivery_price=delivery_price,
        free_delivery_threshold=free_delivery_threshold,
        **kwargs,
    )
    session.add(zone)
    await session.flush()
    return zone


async def make_admin(
    session: AsyncSession,
    *,
    username: str = "admin",
    password: str = "devpass123",
    full_name: str | None = "Test Admin",
    is_active: bool = True,
) -> Admin:
    admin = Admin(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=is_active,
    )
    session.add(admin)
    await session.flush()
    return admin


@pytest.fixture
async def admin_app(test_engine):
    """A real FastAPI app (admin.main.create_app()) with its DB dependency pointed
    at the test engine instead of the production one, so HTTP-level tests hit the
    same real Postgres the other tests use — no mocked DB here either."""
    app = create_app()
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[admin_deps.get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client(admin_app):
    transport = ASGITransport(app=admin_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
