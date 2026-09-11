import pytest
from aiogram import Bot, Dispatcher, Router

# aiogram's handler routers (bot/handlers/*.py) are module-level singletons, and
# Router.include_router() permanently marks a router as attached to its parent —
# calling build_dispatcher() a second time in the same process re-attaches the
# same singleton routers and raises RuntimeError. So this whole file builds the
# dispatcher exactly once (module-scoped fixture) and every test asserts against
# that one shared instance, instead of each test building its own.


def _collect_router_names(router: Router) -> set[str]:
    names = {router.name}
    for sub in router.sub_routers:
        names |= _collect_router_names(sub)
    return names


@pytest.fixture(scope="module")
def dispatcher() -> Dispatcher:
    import bot.main as bot_main

    original_init = Bot.__init__

    def _fail_if_constructed(*args, **kwargs):
        raise AssertionError("Bot() should not be constructed while building the dispatcher")

    Bot.__init__ = _fail_if_constructed
    try:
        return bot_main.build_dispatcher()
    finally:
        Bot.__init__ = original_init


def test_build_dispatcher_returns_a_dispatcher(dispatcher):
    assert isinstance(dispatcher, Dispatcher)


def test_build_dispatcher_registers_all_handler_routers(dispatcher):
    names = _collect_router_names(dispatcher)
    expected = {"root", "start", "language", "gated", "catalog", "cart", "checkout", "orders", "help"}
    assert expected <= names


def test_bot_main_module_imports_cleanly():
    import bot.main as bot_main

    assert hasattr(bot_main, "build_dispatcher")
    assert hasattr(bot_main, "main")
