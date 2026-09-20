from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.auth import hash_password
from admin.deps import get_current_admin, get_db
from app.models.admin import Admin

router = APIRouter(prefix="/admins", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")

TELEGRAM_ID_INVALID = "Telegram ID faqat musbat raqamlardan iborat bo'lishi kerak"


def _parse_telegram_id(raw: str) -> int | None:
    """Empty means "no Telegram account on file" — that is the normal case, so
    a blank field is not an error."""
    raw = raw.strip()
    if not raw:
        return None
    if not raw.isdigit() or int(raw) <= 0:
        raise ValueError(TELEGRAM_ID_INVALID)
    return int(raw)


def _form_response(
    request: Request,
    *,
    admin_user: Admin | None,
    values: dict,
    error: str | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request,
        "admins/form.html",
        {"admin_user": admin_user, "values": values, "error": error},
        status_code=status_code,
    )


async def _active_admin_count(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Admin).where(Admin.is_active.is_(True))
    return (await session.execute(stmt)).scalar_one()


@router.get("")
async def list_admins(request: Request, session: AsyncSession = Depends(get_db)):
    admins = (await session.execute(select(Admin).order_by(Admin.id))).scalars().all()
    return templates.TemplateResponse(request, "admins/list.html", {"admins": admins})


@router.get("/new")
async def new_admin_form(request: Request):
    values = {"username": "", "full_name": "", "telegram_id": ""}
    return _form_response(request, admin_user=None, values=values)


@router.post("/new")
async def create_admin_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    telegram_id: str = Form(""),
    session: AsyncSession = Depends(get_db),
):
    values = {"username": username, "full_name": full_name, "telegram_id": telegram_id}
    try:
        parsed_telegram_id = _parse_telegram_id(telegram_id)
    except ValueError as exc:
        return _form_response(request, admin_user=None, values=values, error=str(exc), status_code=400)
    admin_user = Admin(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name or None,
        telegram_id=parsed_telegram_id,
    )
    session.add(admin_user)
    await session.commit()
    return RedirectResponse(url="/admins", status_code=303)


@router.get("/{admin_id}/edit")
async def edit_admin_form(admin_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    admin_user = await session.get(Admin, admin_id)
    if admin_user is None:
        return RedirectResponse(url="/admins", status_code=303)
    values = {
        "username": admin_user.username,
        "full_name": admin_user.full_name or "",
        "telegram_id": admin_user.telegram_id or "",
    }
    return _form_response(request, admin_user=admin_user, values=values)


@router.post("/{admin_id}/edit")
async def update_admin_user(
    admin_id: int,
    request: Request,
    full_name: str = Form(""),
    telegram_id: str = Form(""),
    session: AsyncSession = Depends(get_db),
):
    admin_user = await session.get(Admin, admin_id)
    if admin_user is None:
        return RedirectResponse(url="/admins", status_code=303)
    values = {"username": admin_user.username, "full_name": full_name, "telegram_id": telegram_id}
    try:
        admin_user.telegram_id = _parse_telegram_id(telegram_id)
    except ValueError as exc:
        return _form_response(
            request, admin_user=admin_user, values=values, error=str(exc), status_code=400
        )
    admin_user.full_name = full_name or None
    await session.commit()
    return RedirectResponse(url="/admins", status_code=303)


@router.post("/{admin_id}/toggle-active")
async def toggle_admin_active(admin_id: int, session: AsyncSession = Depends(get_db)):
    admin_user = await session.get(Admin, admin_id)
    if admin_user is not None:
        admin_user.is_active = not admin_user.is_active
        await session.commit()
    return RedirectResponse(url="/admins", status_code=303)


@router.post("/{admin_id}/delete")
async def delete_admin(
    admin_id: int,
    session: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Hard-delete an admin. Two guards stand between the button and the DELETE:
    the panel must keep at least one active admin (otherwise nobody can log in
    again), and nobody may delete the account they are logged in as.
    """
    admin_user = await session.get(Admin, admin_id)
    if admin_user is None:
        return RedirectResponse(url="/admins", status_code=303)
    # Checked before the self-delete guard on purpose: when only one active
    # admin is left it is necessarily the one making the request, and
    # "there must always be an active admin" is the more informative reason.
    if admin_user.is_active and await _active_admin_count(session) <= 1:
        return RedirectResponse(url="/admins?error=last_active_admin", status_code=303)
    if admin_user.id == current_admin.id:
        return RedirectResponse(url="/admins?error=self_delete", status_code=303)
    await session.delete(admin_user)
    await session.commit()
    return RedirectResponse(url="/admins", status_code=303)
