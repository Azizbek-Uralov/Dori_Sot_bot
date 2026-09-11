from aiogram import Router

from bot.handlers import cart, catalog, checkout, help as help_handlers, language, orders, start
from bot.middlewares.subscription_gate import SubscriptionMiddleware

start_router = start.router
language_router = language.router


def _build_gated_router() -> Router:
    gated = Router(name="gated")
    gated.message.middleware(SubscriptionMiddleware())
    gated.callback_query.middleware(SubscriptionMiddleware())
    gated.include_router(catalog.router)
    gated.include_router(cart.router)
    gated.include_router(checkout.router)
    gated.include_router(orders.router)
    gated.include_router(help_handlers.router)
    return gated


def build_root_router() -> Router:
    root = Router(name="root")
    root.include_router(start_router)
    root.include_router(language_router)
    root.include_router(_build_gated_router())
    return root
