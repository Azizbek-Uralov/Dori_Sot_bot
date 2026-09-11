from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from app.models.category import Category
from app.services import catalog_service

router = APIRouter(prefix="/categories", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


@router.get("")
async def list_categories(request: Request, session: AsyncSession = Depends(get_db)):
    categories = await catalog_service.list_categories(session, active_only=False)
    return templates.TemplateResponse(request, "categories/list.html", {"categories": categories})


@router.get("/new")
async def new_category_form(request: Request):
    return templates.TemplateResponse(request, "categories/form.html", {"category": None})


@router.post("/new")
async def create_category(
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    display_order: int = Form(0),
    session: AsyncSession = Depends(get_db),
):
    session.add(Category(name_uz=name_uz, name_ru=name_ru, display_order=display_order))
    await session.commit()
    return RedirectResponse(url="/categories", status_code=303)


@router.get("/{category_id}/edit")
async def edit_category_form(category_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    category = await catalog_service.get_category(session, category_id)
    return templates.TemplateResponse(request, "categories/form.html", {"category": category})


@router.post("/{category_id}/edit")
async def update_category(
    category_id: int,
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    display_order: int = Form(0),
    session: AsyncSession = Depends(get_db),
):
    category = await catalog_service.get_category(session, category_id)
    if category is not None:
        category.name_uz = name_uz
        category.name_ru = name_ru
        category.display_order = display_order
        await session.commit()
    return RedirectResponse(url="/categories", status_code=303)


@router.post("/{category_id}/toggle-active")
async def toggle_category_active(category_id: int, session: AsyncSession = Depends(get_db)):
    category = await catalog_service.get_category(session, category_id)
    if category is not None:
        category.is_active = not category.is_active
        await session.commit()
    return RedirectResponse(url="/categories", status_code=303)
