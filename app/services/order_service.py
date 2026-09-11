from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import MIN_ORDER_TOTAL, Language, OrderStatus, ORDER_STATUS_TRANSITIONS
from app.models.delivery_zone import DeliveryZone
from app.models.order import Order, OrderItem
from app.models.user import User
from app.services import cart_service, delivery_service


class MinOrderNotMetError(Exception):
    def __init__(self, current_total: int, min_total: int = MIN_ORDER_TOTAL):
        self.current_total = current_total
        self.min_total = min_total
        self.shortfall = min_total - current_total
        super().__init__(f"Order total {current_total} is below minimum {min_total}")


class InsufficientStockError(Exception):
    def __init__(self, product_name_uz: str, product_name_ru: str, available: int):
        self.product_name_uz = product_name_uz
        self.product_name_ru = product_name_ru
        self.available = available
        super().__init__(f"Insufficient stock for {product_name_uz}: {available} available")


class InvalidStatusTransitionError(Exception):
    def __init__(self, current: OrderStatus, target: OrderStatus):
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition order from {current} to {target}")


def validate_min_order(items_subtotal: int) -> None:
    if items_subtotal < MIN_ORDER_TOTAL:
        raise MinOrderNotMetError(current_total=items_subtotal)


async def create_order(
    session: AsyncSession,
    user: User,
    full_name: str,
    phone: str,
    zone: DeliveryZone,
    delivery_address_text: str,
    customer_language: Language,
) -> Order:
    summary = await cart_service.get_summary(session, user)
    validate_min_order(summary.subtotal)

    for line in summary.lines:
        if line.quantity > line.product.stock_quantity or not line.product.is_active:
            raise InsufficientStockError(
                product_name_uz=line.product.name_uz,
                product_name_ru=line.product.name_ru,
                available=line.product.stock_quantity,
            )

    delivery_fee = delivery_service.compute_fee(zone, summary.subtotal)
    grand_total = summary.subtotal + delivery_fee

    order = Order(
        user_id=user.id,
        customer_name=full_name,
        customer_phone=phone,
        delivery_zone_id=zone.id,
        delivery_address_text=delivery_address_text,
        items_subtotal=summary.subtotal,
        delivery_fee=delivery_fee,
        grand_total=grand_total,
        status=OrderStatus.NEW,
        customer_language=customer_language,
    )
    # Set before add()/flush(), while `order` is still transient: assigning a
    # relationship reads its current value first (for cascade bookkeeping), and
    # that read is itself a lazy load once the object is persistent — see
    # get_or_create_cart for the same fix on Cart.items, done in the same order.
    order.items = []
    session.add(order)
    await session.flush()

    for line in summary.lines:
        order.items.append(
            OrderItem(
                product_id=line.product.id,
                product_name_uz=line.product.name_uz,
                product_name_ru=line.product.name_ru,
                unit_price=line.product.price,
                quantity=line.quantity,
                line_total=line.line_total,
            )
        )
        line.product.stock_quantity -= line.quantity

    user.full_name = full_name
    user.phone = phone

    await cart_service.clear_cart(session, user)
    await session.commit()
    await session.refresh(order, attribute_names=["created_at", "updated_at"])
    return order


async def transition_status(session: AsyncSession, order: Order, new_status: OrderStatus) -> Order:
    allowed = ORDER_STATUS_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise InvalidStatusTransitionError(current=order.status, target=new_status)
    order.status = new_status
    await session.commit()
    await session.refresh(order, attribute_names=["updated_at"])
    return order


async def get_order(session: AsyncSession, order_id: int) -> Order | None:
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.delivery_zone), selectinload(Order.user))
        .where(Order.id == order_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_orders_for_user(session: AsyncSession, user_id: int) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_orders(
    session: AsyncSession,
    status: OrderStatus | None = None,
    date_from=None,
    date_to=None,
) -> list[Order]:
    stmt = select(Order).options(selectinload(Order.user)).order_by(Order.created_at.desc())
    if status is not None:
        stmt = stmt.where(Order.status == status)
    if date_from is not None:
        stmt = stmt.where(Order.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Order.created_at <= date_to)
    return list((await session.execute(stmt)).scalars().all())
