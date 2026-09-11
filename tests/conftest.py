import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (registers every model on Base.metadata)
from app.config import settings
from app.constants import Language
from app.db import Base
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
