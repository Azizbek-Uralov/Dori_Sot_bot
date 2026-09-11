import pytest

from app.constants import MIN_ORDER_TOTAL, Language, OrderStatus
from app.services import cart_service, order_service
from app.services.order_service import (
    InsufficientStockError,
    InvalidStatusTransitionError,
    MinOrderNotMetError,
)
from tests.conftest import make_category, make_product, make_user, make_zone


def test_validate_min_order_raises_below_minimum():
    with pytest.raises(MinOrderNotMetError) as exc_info:
        order_service.validate_min_order(MIN_ORDER_TOTAL - 1)
    assert exc_info.value.shortfall == 1


def test_validate_min_order_passes_at_minimum():
    order_service.validate_min_order(MIN_ORDER_TOTAL)


def test_validate_min_order_passes_above_minimum():
    order_service.validate_min_order(MIN_ORDER_TOTAL + 1000)


async def test_create_order_rejects_below_minimum(db_session):
    user = await make_user(db_session, telegram_id=100)
    category = await make_category(db_session)
    cheap_product = await make_product(db_session, category=category, price=1000, stock_quantity=10)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, cheap_product.id, quantity=1)

    with pytest.raises(MinOrderNotMetError):
        await order_service.create_order(
            db_session,
            user=user,
            full_name="Ali Aliyev",
            phone="+998901234567",
            zone=zone,
            delivery_address_text="Chilonzor, 1-uy",
            customer_language=Language.UZ,
        )


async def test_create_order_rejects_insufficient_stock(db_session):
    user = await make_user(db_session, telegram_id=101)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=MIN_ORDER_TOTAL, stock_quantity=1)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=2)

    with pytest.raises(InsufficientStockError):
        await order_service.create_order(
            db_session,
            user=user,
            full_name="Ali Aliyev",
            phone="+998901234567",
            zone=zone,
            delivery_address_text="Chilonzor, 1-uy",
            customer_language=Language.UZ,
        )


async def test_create_order_rejects_inactive_product(db_session):
    user = await make_user(db_session, telegram_id=102)
    category = await make_category(db_session)
    product = await make_product(
        db_session, category=category, price=MIN_ORDER_TOTAL, stock_quantity=10, is_active=True
    )
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=1)
    product.is_active = False
    await db_session.flush()

    with pytest.raises(InsufficientStockError):
        await order_service.create_order(
            db_session,
            user=user,
            full_name="Ali Aliyev",
            phone="+998901234567",
            zone=zone,
            delivery_address_text="Chilonzor, 1-uy",
            customer_language=Language.UZ,
        )


async def test_create_order_snapshots_items_and_decrements_stock(db_session):
    user = await make_user(db_session, telegram_id=103)
    category = await make_category(db_session)
    product = await make_product(
        db_session,
        category=category,
        name_uz="Vitamin C",
        name_ru="Витамин C",
        price=60000,
        stock_quantity=10,
    )
    zone = await make_zone(db_session, delivery_price=15000, free_delivery_threshold=None)
    await cart_service.add_item(db_session, user, product.id, quantity=1)

    order = await order_service.create_order(
        db_session,
        user=user,
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone=zone,
        delivery_address_text="Chilonzor, 1-uy",
        customer_language=Language.UZ,
    )

    assert order.items_subtotal == 60000
    assert order.delivery_fee == 15000
    assert order.grand_total == 75000
    assert order.status == OrderStatus.NEW
    assert product.stock_quantity == 9

    # create_order's return value itself must carry its items without a
    # re-query: order.items was appended to via the relationship (not a raw
    # order_id FK), so this is a plain read rather than a lazy load.
    assert len(order.items) == 1
    line = order.items[0]
    assert line.product_name_uz == "Vitamin C"
    assert line.product_name_ru == "Витамин C"
    assert line.unit_price == 60000
    assert line.quantity == 1
    assert line.line_total == 60000

    reloaded = await order_service.get_order(db_session, order.id)
    assert len(reloaded.items) == 1


async def test_create_order_applies_free_delivery_threshold(db_session):
    user = await make_user(db_session, telegram_id=104)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session, delivery_price=15000, free_delivery_threshold=50000)
    await cart_service.add_item(db_session, user, product.id, quantity=1)

    order = await order_service.create_order(
        db_session,
        user=user,
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone=zone,
        delivery_address_text="Chilonzor, 1-uy",
        customer_language=Language.UZ,
    )

    assert order.delivery_fee == 0
    assert order.grand_total == 60000


async def test_create_order_clears_cart(db_session):
    user = await make_user(db_session, telegram_id=105)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=1)

    await order_service.create_order(
        db_session,
        user=user,
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone=zone,
        delivery_address_text="Chilonzor, 1-uy",
        customer_language=Language.UZ,
    )

    summary = await cart_service.get_summary(db_session, user)
    assert summary.lines == []


async def test_transition_status_allows_forward_path(db_session):
    user = await make_user(db_session, telegram_id=106)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=1)
    order = await order_service.create_order(
        db_session,
        user=user,
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone=zone,
        delivery_address_text="Chilonzor, 1-uy",
        customer_language=Language.UZ,
    )

    order = await order_service.transition_status(db_session, order, OrderStatus.CONFIRMED)
    assert order.status == OrderStatus.CONFIRMED

    order = await order_service.transition_status(db_session, order, OrderStatus.DELIVERING)
    assert order.status == OrderStatus.DELIVERING

    order = await order_service.transition_status(db_session, order, OrderStatus.DELIVERED)
    assert order.status == OrderStatus.DELIVERED


async def test_transition_status_rejects_skipping_states(db_session):
    user = await make_user(db_session, telegram_id=107)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=1)
    order = await order_service.create_order(
        db_session,
        user=user,
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone=zone,
        delivery_address_text="Chilonzor, 1-uy",
        customer_language=Language.UZ,
    )

    with pytest.raises(InvalidStatusTransitionError):
        await order_service.transition_status(db_session, order, OrderStatus.DELIVERED)


async def test_transition_status_keeps_relationships_accessible(db_session):
    """Regression test mirroring admin/routers/orders.py: get_order() eager-loads
    items/delivery_zone/user, then transition_status() commits + refreshes the
    order. That refresh must not expire those relationships, since notify_service
    (order.items, order.user.telegram_id) reads them right after without a
    re-query — an unscoped session.refresh() previously left them needing a lazy
    load, which raises MissingGreenlet under AsyncSession."""
    user = await make_user(db_session, telegram_id=109)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=1)
    created = await order_service.create_order(
        db_session,
        user=user,
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone=zone,
        delivery_address_text="Chilonzor, 1-uy",
        customer_language=Language.UZ,
    )

    order = await order_service.get_order(db_session, created.id)
    order = await order_service.transition_status(db_session, order, OrderStatus.CONFIRMED)

    assert len(order.items) == 1
    assert order.user.id == user.id
    assert order.delivery_zone.id == zone.id


async def test_transition_status_terminal_states_reject_everything(db_session):
    user = await make_user(db_session, telegram_id=108)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=1)
    order = await order_service.create_order(
        db_session,
        user=user,
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone=zone,
        delivery_address_text="Chilonzor, 1-uy",
        customer_language=Language.UZ,
    )
    order = await order_service.transition_status(db_session, order, OrderStatus.CANCELLED)

    with pytest.raises(InvalidStatusTransitionError):
        await order_service.transition_status(db_session, order, OrderStatus.CONFIRMED)
