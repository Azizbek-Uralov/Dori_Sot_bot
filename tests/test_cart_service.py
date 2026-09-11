from app.services import cart_service
from tests.conftest import make_category, make_product, make_user


async def test_add_item_creates_cart_item(db_session):
    user = await make_user(db_session, telegram_id=1)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=20000)

    item = await cart_service.add_item(db_session, user, product.id, quantity=2)

    assert item.product_id == product.id
    assert item.quantity == 2


async def test_add_existing_item_increments_quantity(db_session):
    user = await make_user(db_session, telegram_id=2)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category)

    await cart_service.add_item(db_session, user, product.id, quantity=2)
    item = await cart_service.add_item(db_session, user, product.id, quantity=3)

    assert item.quantity == 5


async def test_set_quantity_updates_existing_item(db_session):
    user = await make_user(db_session, telegram_id=3)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category)
    await cart_service.add_item(db_session, user, product.id, quantity=1)

    await cart_service.set_quantity(db_session, user, product.id, quantity=7)

    summary = await cart_service.get_summary(db_session, user)
    assert summary.lines[0].quantity == 7


async def test_set_quantity_zero_removes_item(db_session):
    user = await make_user(db_session, telegram_id=4)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category)
    await cart_service.add_item(db_session, user, product.id, quantity=1)

    await cart_service.set_quantity(db_session, user, product.id, quantity=0)

    summary = await cart_service.get_summary(db_session, user)
    assert summary.lines == []


async def test_remove_item(db_session):
    user = await make_user(db_session, telegram_id=5)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category)
    await cart_service.add_item(db_session, user, product.id, quantity=1)

    await cart_service.remove_item(db_session, user, product.id)

    summary = await cart_service.get_summary(db_session, user)
    assert summary.lines == []


async def test_clear_cart_removes_all_items(db_session):
    user = await make_user(db_session, telegram_id=6)
    category = await make_category(db_session)
    product_a = await make_product(db_session, category=category, name_uz="A")
    product_b = await make_product(db_session, category=category, name_uz="B")
    await cart_service.add_item(db_session, user, product_a.id, quantity=1)
    await cart_service.add_item(db_session, user, product_b.id, quantity=1)

    await cart_service.clear_cart(db_session, user)

    summary = await cart_service.get_summary(db_session, user)
    assert summary.lines == []
    assert summary.subtotal == 0


async def test_get_summary_computes_subtotal(db_session):
    user = await make_user(db_session, telegram_id=7)
    category = await make_category(db_session)
    product_a = await make_product(db_session, category=category, name_uz="A", price=10000)
    product_b = await make_product(db_session, category=category, name_uz="B", price=25000)
    await cart_service.add_item(db_session, user, product_a.id, quantity=2)
    await cart_service.add_item(db_session, user, product_b.id, quantity=1)

    summary = await cart_service.get_summary(db_session, user)

    assert summary.subtotal == 2 * 10000 + 1 * 25000
