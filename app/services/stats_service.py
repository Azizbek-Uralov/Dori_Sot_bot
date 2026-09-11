from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import OrderStatus
from app.models.order import Order, OrderItem


async def sales_totals(
    session: AsyncSession, date_from: datetime | None = None, date_to: datetime | None = None
) -> dict:
    stmt = select(
        func.count(Order.id).label("orders_count"),
        func.coalesce(func.sum(Order.grand_total), 0).label("total_revenue"),
    ).where(Order.status != OrderStatus.CANCELLED)
    if date_from is not None:
        stmt = stmt.where(Order.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Order.created_at <= date_to)
    row = (await session.execute(stmt)).one()
    return {"orders_count": row.orders_count, "total_revenue": int(row.total_revenue)}


async def best_selling_products(session: AsyncSession, limit: int = 10) -> list[dict]:
    stmt = (
        select(
            OrderItem.product_name_uz,
            OrderItem.product_name_ru,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.line_total).label("total_revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status != OrderStatus.CANCELLED)
        .group_by(OrderItem.product_name_uz, OrderItem.product_name_ru)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "name_uz": row.product_name_uz,
            "name_ru": row.product_name_ru,
            "total_qty": row.total_qty,
            "total_revenue": int(row.total_revenue),
        }
        for row in rows
    ]


async def orders_by_status(session: AsyncSession) -> dict[OrderStatus, int]:
    stmt = select(Order.status, func.count(Order.id)).group_by(Order.status)
    rows = (await session.execute(stmt)).all()
    counts = {status: 0 for status in OrderStatus}
    for status, count in rows:
        counts[status] = count
    return counts
