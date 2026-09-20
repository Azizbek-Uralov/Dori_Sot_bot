from aiogram.exceptions import TelegramAPIError

from app.constants import Language
from app.services import notify_service
from tests.conftest import make_admin, make_category, make_product, make_user, make_zone
from app.services import cart_service, order_service


class FakeBot:
    """Stand-in for aiogram.Bot: records every send_message call and can be
    told to raise for specific chat ids, without touching the network."""

    def __init__(self, failing_chat_ids: set[int] | None = None):
        self.sent: list[tuple[int | str, str]] = []
        self.failing_chat_ids = failing_chat_ids or set()

    async def send_message(self, chat_id, text):
        if chat_id in self.failing_chat_ids:
            raise TelegramAPIError(method=None, message="boom")
        self.sent.append((chat_id, text))


async def _make_order(db_session, *, telegram_id: int = 700):
    user = await make_user(db_session, telegram_id=telegram_id)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session, name_uz="Chilonzor")
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
    return await order_service.get_order(db_session, order.id)


def test_render_admin_order_text_includes_zone_name():
    class FakeZone:
        name_uz = "Chilonzor"

    class FakeItem:
        product_name_uz = "Vitamin C"
        quantity = 2
        line_total = 40000

    class FakeOrder:
        id = 1
        customer_name = "Ali Aliyev"
        customer_phone = "+998901234567"
        items = [FakeItem()]
        items_subtotal = 40000
        delivery_fee = 15000
        grand_total = 55000
        delivery_zone = FakeZone()
        delivery_address_text = "Chilonzor, 1-uy"

    text = notify_service.render_admin_order_text(FakeOrder())

    assert "Hudud: Chilonzor" in text
    assert "Manzil: Chilonzor, 1-uy" in text
    assert "№1" in text


async def test_notify_admins_direct_sends_to_active_admins_with_telegram_id(db_session, monkeypatch):
    order = await _make_order(db_session)
    await make_admin(db_session, username="a1", telegram_id=111, is_active=True)
    await make_admin(db_session, username="a2", telegram_id=222, is_active=True)
    await db_session.commit()

    fake_bot = FakeBot()
    monkeypatch.setattr(notify_service, "get_bot", lambda: fake_bot)

    sent_count = await notify_service.notify_admins_direct(db_session, order)

    assert sent_count == 2
    assert {chat_id for chat_id, _ in fake_bot.sent} == {111, 222}
    assert "Ali Aliyev" in fake_bot.sent[0][1]


async def test_notify_admins_direct_skips_admins_without_telegram_id(db_session, monkeypatch):
    order = await _make_order(db_session)
    await make_admin(db_session, username="a1", telegram_id=None, is_active=True)
    await db_session.commit()

    fake_bot = FakeBot()
    monkeypatch.setattr(notify_service, "get_bot", lambda: fake_bot)

    sent_count = await notify_service.notify_admins_direct(db_session, order)

    assert sent_count == 0
    assert fake_bot.sent == []


async def test_notify_admins_direct_skips_inactive_admins(db_session, monkeypatch):
    order = await _make_order(db_session)
    await make_admin(db_session, username="retired", telegram_id=333, is_active=False)
    await db_session.commit()

    fake_bot = FakeBot()
    monkeypatch.setattr(notify_service, "get_bot", lambda: fake_bot)

    sent_count = await notify_service.notify_admins_direct(db_session, order)

    assert sent_count == 0
    assert fake_bot.sent == []


async def test_notify_admins_direct_continues_after_one_admin_fails(db_session, monkeypatch):
    # one admin blocking the bot must not cost the others their notification
    order = await _make_order(db_session)
    await make_admin(db_session, username="blocked", telegram_id=111, is_active=True)
    await make_admin(db_session, username="reachable", telegram_id=222, is_active=True)
    await db_session.commit()

    fake_bot = FakeBot(failing_chat_ids={111})
    monkeypatch.setattr(notify_service, "get_bot", lambda: fake_bot)

    sent_count = await notify_service.notify_admins_direct(db_session, order)

    assert sent_count == 1
    assert fake_bot.sent == [(222, fake_bot.sent[0][1])]


async def test_notify_admins_direct_returns_zero_when_bot_unavailable(db_session, monkeypatch):
    order = await _make_order(db_session)
    await make_admin(db_session, username="a1", telegram_id=111, is_active=True)
    await db_session.commit()

    monkeypatch.setattr(notify_service, "get_bot", lambda: None)

    sent_count = await notify_service.notify_admins_direct(db_session, order)

    assert sent_count == 0


async def test_notify_admins_direct_returns_zero_when_no_admins_configured(db_session, monkeypatch):
    order = await _make_order(db_session)
    await db_session.commit()

    fake_bot = FakeBot()
    monkeypatch.setattr(notify_service, "get_bot", lambda: fake_bot)

    sent_count = await notify_service.notify_admins_direct(db_session, order)

    assert sent_count == 0
    assert fake_bot.sent == []
