from app.services import cart_service
from tests.conftest import make_category, make_product, make_user


async def test_open_cart_for_first_time_user_with_no_cart_row(db_session):
    """Regression test: a user who never added anything has no carts row at
    all yet. get_or_create_cart's "create" branch used to leave the new Cart's
    .items collection untouched; once the object became persistent (post
    flush), SQLAlchemy no longer assumes an untouched collection is empty and
    tried to lazy-load it on first access instead, raising MissingGreenlet
    under AsyncSession — exactly what bot/handlers/cart.py's open_cart hits
    for a brand-new user pressing "Savatcha" before adding anything."""
    user = await make_user(db_session, telegram_id=200)

    summary = await cart_service.get_summary(db_session, user)

    assert summary.lines == []
    assert summary.subtotal == 0


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


async def test_open_cart_after_adding_item_in_same_session(db_session):
    """Regression test for the "add to cart, then open cart" flow: within a single
    request (one AsyncSession, mirroring bot/handlers/cart.py), accessing the
    relationships involved must not trigger a lazy load, which would raise
    MissingGreenlet under AsyncSession instead of working like plain sync code."""
    user = await make_user(db_session, telegram_id=8)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, name_uz="Vitamin D", price=30000)

    item = await cart_service.add_item(db_session, user, product.id, quantity=2)
    # add_item's session.refresh() must not expire the item's relationships.
    assert item.cart is not None
    assert item.product.name_uz == "Vitamin D"

    cart = await cart_service.get_or_create_cart(db_session, user)
    assert [line.quantity for line in cart.items] == [2]
    assert cart.items[0].product.name_uz == "Vitamin D"

    summary = await cart_service.get_summary(db_session, user)
    assert len(summary.lines) == 1
    assert summary.lines[0].product.name_uz == "Vitamin D"
    assert summary.subtotal == 60000
