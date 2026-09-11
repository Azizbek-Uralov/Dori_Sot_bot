from app.constants import Language, OrderStatus
from app.models.order import Order
from app.services import cart_service, notify_service, order_service
from tests.conftest import make_admin, make_category, make_product, make_user, make_zone


async def _login(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()
    await admin_client.post("/login", data={"username": "admin", "password": "devpass123"})


async def _make_order(db_session) -> Order:
    user = await make_user(db_session, telegram_id=500)
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
    return order


async def test_orders_list_requires_login(admin_client, db_session):
    response = await admin_client.get("/orders")
    assert response.status_code == 303


async def test_orders_list_renders(admin_client, db_session):
    await _login(admin_client, db_session)
    await _make_order(db_session)

    response = await admin_client.get("/orders")

    assert response.status_code == 200


async def test_orders_list_filters_by_status(admin_client, db_session):
    await _login(admin_client, db_session)
    await _make_order(db_session)

    response = await admin_client.get("/orders", params={"status": "confirmed"})

    assert response.status_code == 200


async def test_order_detail_renders(admin_client, db_session):
    await _login(admin_client, db_session)
    order = await _make_order(db_session)

    response = await admin_client.get(f"/orders/{order.id}")

    assert response.status_code == 200


async def test_valid_status_transition_updates_db_and_notifies_customer(admin_client, db_session, monkeypatch):
    await _login(admin_client, db_session)
    order = await _make_order(db_session)

    recorded = []

    async def fake_notify(order_arg, new_status_arg):
        recorded.append((order_arg.id, new_status_arg))
        return True

    monkeypatch.setattr(notify_service, "notify_customer_status_change", fake_notify)

    response = await admin_client.post(f"/orders/{order.id}/status", data={"new_status": "confirmed"})

    assert response.status_code == 303
    assert response.headers["location"] == f"/orders/{order.id}"
    assert recorded == [(order.id, OrderStatus.CONFIRMED)]

    await db_session.refresh(order)
    assert order.status == OrderStatus.CONFIRMED


async def test_invalid_status_transition_rejected_and_db_unchanged(admin_client, db_session, monkeypatch):
    await _login(admin_client, db_session)
    order = await _make_order(db_session)

    recorded = []

    async def fake_notify(order_arg, new_status_arg):
        recorded.append((order_arg.id, new_status_arg))
        return True

    monkeypatch.setattr(notify_service, "notify_customer_status_change", fake_notify)

    response = await admin_client.post(f"/orders/{order.id}/status", data={"new_status": "delivered"})

    assert response.status_code == 303
    assert response.headers["location"] == f"/orders/{order.id}?error=invalid_transition"
    assert recorded == []

    await db_session.refresh(order)
    assert order.status == OrderStatus.NEW


async def test_status_change_commits_even_if_notify_fails(admin_client, db_session, monkeypatch):
    await _login(admin_client, db_session)
    order = await _make_order(db_session)

    async def failing_notify(order_arg, new_status_arg):
        return False

    monkeypatch.setattr(notify_service, "notify_customer_status_change", failing_notify)

    response = await admin_client.post(f"/orders/{order.id}/status", data={"new_status": "confirmed"})

    assert response.status_code == 303
    await db_session.refresh(order)
    assert order.status == OrderStatus.CONFIRMED
