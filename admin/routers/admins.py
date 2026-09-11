from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import hash_password
from admin.deps import get_current_admin, get_db
from app.models.admin import Admin

router = APIRouter(prefix="/admins", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


@router.get("")
async def list_admins(request: Request, session: AsyncSession = Depends(get_db)):
    admins = (await session.execute(select(Admin).order_by(Admin.id))).scalars().all()
    return templates.TemplateResponse(request, "admins/list.html", {"admins": admins})


@router.get("/new")
async def new_admin_form(request: Request):
    return templates.TemplateResponse(request, "admins/form.html", {})


@router.post("/new")
async def create_admin_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    session: AsyncSession = Depends(get_db),
):
    admin_user = Admin(username=username, password_hash=hash_password(password), full_name=full_name or None)
    session.add(admin_user)
    await session.commit()
    return RedirectResponse(url="/admins", status_code=303)


@router.post("/{admin_id}/toggle-active")
async def toggle_admin_active(admin_id: int, session: AsyncSession = Depends(get_db)):
    admin_user = await session.get(Admin, admin_id)
    if admin_user is not None:
        admin_user.is_active = not admin_user.is_active
        await session.commit()
    return RedirectResponse(url="/admins", status_code=303)
