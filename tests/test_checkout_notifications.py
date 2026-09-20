"""Covers the new-order notification wiring end to end: confirming a checkout
must trigger both the group notification and the direct-to-admin DMs, and a
DM failure must never block the order itself.
"""

from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select

from app.constants import Language
from app.models.order import Order
from app.services import cart_service, notify_service
from bot.handlers.checkout import confirm_order
from bot.states.checkout import CheckoutStates
from bot.utils.callback_data import OrderConfirmCB
from tests.conftest import make_category, make_product, make_user, make_zone


class FakeMessage:
    def __init__(self):
        self.answers: list[str] = []

    async def answer(self, text, reply_markup=None):
        self.answers.append(text)


class FakeCallbackQuery:
    def __init__(self, message: FakeMessage):
        self.message = message

    async def answer(self):
        pass


async def _fsm_context() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    return FSMContext(storage=storage, key=key)


async def _prepare_pending_checkout(db_session, *, telegram_id: int = 900):
    user = await make_user(db_session, telegram_id=telegram_id, language=Language.UZ)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, price=60000, stock_quantity=10)
    zone = await make_zone(db_session)
    await cart_service.add_item(db_session, user, product.id, quantity=1)

    state = await _fsm_context()
    await state.set_state(CheckoutStates.waiting_confirm)
    await state.update_data(
        full_name="Ali Aliyev",
        phone="+998901234567",
        zone_id=zone.id,
        address="Chilonzor, 1-uy",
        items_subtotal=60000,
    )
    return user, state


@pytest.fixture(autouse=True)
def _reset_bot_singleton():
    # get_bot() memoizes a module-level Bot; make sure each test's monkeypatch
    # of get_bot doesn't leak into other test files.
    yield
    notify_service._bot = None
    notify_service._bot_construction_failed = False


async def test_confirming_order_notifies_group_and_direct_admins(db_session, monkeypatch):
    user, state = await _prepare_pending_checkout(db_session)

    group_mock = AsyncMock(return_value=True)
    direct_mock = AsyncMock(return_value=2)
    monkeypatch.setattr(notify_service, "notify_admin_group", group_mock)
    monkeypatch.setattr(notify_service, "notify_admins_direct", direct_mock)

    message = FakeMessage()
    callback = FakeCallbackQuery(message)
    callback_data = OrderConfirmCB(action="confirm")

    await confirm_order(callback, callback_data, state, db_session, user)

    group_mock.assert_awaited_once()
    direct_mock.assert_awaited_once()
    # notify_admins_direct takes (session, order), not just the order
    direct_args = direct_mock.await_args.args
    assert direct_args[0] is db_session


async def test_admin_notified_at_set_when_only_direct_notification_succeeds(db_session, monkeypatch):
    # the group send can fail (e.g. bad chat id) while DMs still go through;
    # admin_notified_at must reflect that the admins were reached at all
    user, state = await _prepare_pending_checkout(db_session)

    monkeypatch.setattr(notify_service, "notify_admin_group", AsyncMock(return_value=False))
    monkeypatch.setattr(notify_service, "notify_admins_direct", AsyncMock(return_value=1))

    message = FakeMessage()
    callback = FakeCallbackQuery(message)
    callback_data = OrderConfirmCB(action="confirm")

    await confirm_order(callback, callback_data, state, db_session, user)

    order = (await db_session.execute(select(Order))).scalar_one()
    assert order.admin_notified_at is not None


async def test_admin_notified_at_stays_null_when_both_notifications_fail(db_session, monkeypatch):
    user, state = await _prepare_pending_checkout(db_session)

    monkeypatch.setattr(notify_service, "notify_admin_group", AsyncMock(return_value=False))
    monkeypatch.setattr(notify_service, "notify_admins_direct", AsyncMock(return_value=0))

    message = FakeMessage()
    callback = FakeCallbackQuery(message)
    callback_data = OrderConfirmCB(action="confirm")

    await confirm_order(callback, callback_data, state, db_session, user)

    order = (await db_session.execute(select(Order))).scalar_one()
    assert order.admin_notified_at is None
    # the order itself must still succeed regardless of notification outcome
    assert len(message.answers) == 1
    assert str(order.id) in message.answers[0]
