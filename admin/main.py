from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from admin.deps import NotAuthenticated
from admin.routers import admins, auth, categories, customers, dashboard, delivery_zones, orders, products, stats
from app.config import settings
from app.services.notify_service import close_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_bot()


def create_app() -> FastAPI:
    app = FastAPI(title="DorSotBot Admin", lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.admin_session_secret,
        max_age=settings.admin_session_max_age_seconds,
    )
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.exception_handler(NotAuthenticated)
    async def not_authenticated_handler(request: Request, exc: NotAuthenticated):
        return RedirectResponse(url="/login", status_code=303)

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(categories.router)
    app.include_router(products.router)
    app.include_router(delivery_zones.router)
    app.include_router(orders.router)
    app.include_router(customers.router)
    app.include_router(admins.router)
    app.include_router(stats.router)
    return app


app = create_app()
