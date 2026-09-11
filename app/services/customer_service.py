from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import OrderStatus
from app.models.order import Order
from app.models.user import User


@dataclass
class CustomerStats:
    user: User
    order_count: int
    lifetime_spend: int


async def list_customers_with_stats(session: AsyncSession) -> list[CustomerStats]:
    stmt = (
        select(
            User,
            func.count(Order.id).label("order_count"),
            func.coalesce(
                func.sum(Order.grand_total).filter(Order.status != OrderStatus.CANCELLED), 0
            ).label("lifetime_spend"),
        )
        .join(Order, Order.user_id == User.id, isouter=True)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        CustomerStats(user=row.User, order_count=row.order_count, lifetime_spend=int(row.lifetime_spend))
        for row in rows
    ]


async def get_customer(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)
