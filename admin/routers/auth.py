from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import verify_password
from admin.deps import get_db
from app.models.admin import Admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Admin).where(Admin.username == username)
    admin = (await session.execute(stmt)).scalar_one_or_none()
    if admin is None or not admin.is_active or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Login yoki parol noto'g'ri"}, status_code=401
        )
    request.session["admin_id"] = admin.id
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
