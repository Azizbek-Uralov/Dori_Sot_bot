from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product


async def list_categories(session: AsyncSession, active_only: bool = True) -> list[Category]:
    stmt = select(Category).order_by(Category.display_order, Category.id)
    if active_only:
        stmt = stmt.where(Category.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_category(session: AsyncSession, category_id: int) -> Category | None:
    return await session.get(Category, category_id)


async def list_products(
    session: AsyncSession, category_id: int, active_only: bool = True
) -> list[Product]:
    stmt = select(Product).where(Product.category_id == category_id).order_by(Product.id)
    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_product(session: AsyncSession, product_id: int) -> Product | None:
    return await session.get(Product, product_id)
