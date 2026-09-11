from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_zone import DeliveryZone


async def list_zones(session: AsyncSession, active_only: bool = True) -> list[DeliveryZone]:
    stmt = select(DeliveryZone).order_by(DeliveryZone.display_order, DeliveryZone.id)
    if active_only:
        stmt = stmt.where(DeliveryZone.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_zone(session: AsyncSession, zone_id: int) -> DeliveryZone | None:
    return await session.get(DeliveryZone, zone_id)


def compute_fee(zone: DeliveryZone, items_subtotal: int) -> int:
    if zone.free_delivery_threshold is not None and items_subtotal >= zone.free_delivery_threshold:
        return 0
    return zone.delivery_price
