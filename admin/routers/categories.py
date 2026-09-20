from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from app.models.category import Category
from app.models.product import Product
from app.services import catalog_service

router = APIRouter(prefix="/categories", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")

DISPLAY_ORDER_NOT_POSITIVE = "Tartib raqam musbat butun son bo'lishi kerak (eng kamida 1)"
DISPLAY_ORDER_TAKEN = "Bu tartib raqam allaqachon band"


async def _taken_display_orders(session: AsyncSession, exclude_id: int | None = None) -> list[int]:
    """Display orders already in use, for the form hint and the clash check.
    Rows left at the old 0 default are dropped: 0 can never clash with a valid
    (>= 1) input, so showing it would only confuse. When editing, the category's
    own number is not "taken" by anyone else."""
    stmt = select(Category.display_order).where(Category.display_order >= 1)
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    return sorted({row for row in (await session.execute(stmt)).scalars().all()})


def _validate_display_order(display_order: int, taken: list[int]) -> str | None:
    if display_order < 1:
        return DISPLAY_ORDER_NOT_POSITIVE
    if display_order in taken:
        return DISPLAY_ORDER_TAKEN
    return None


def _form_response(
    request: Request,
    *,
    category: Category | None,
    values: dict,
    taken: list[int],
    error: str | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request,
        "categories/form.html",
        {"category": category, "values": values, "taken_orders": taken, "error": error},
        status_code=status_code,
    )


@router.get("")
async def list_categories(request: Request, session: AsyncSession = Depends(get_db)):
    categories = await catalog_service.list_categories(session, active_only=False)
    return templates.TemplateResponse(request, "categories/list.html", {"categories": categories})


@router.get("/new")
async def new_category_form(request: Request, session: AsyncSession = Depends(get_db)):
    taken = await _taken_display_orders(session)
    values = {"name_uz": "", "name_ru": "", "display_order": max(taken, default=0) + 1}
    return _form_response(request, category=None, values=values, taken=taken)


@router.post("/new")
async def create_category(
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    display_order: int = Form(...),
    session: AsyncSession = Depends(get_db),
):
    taken = await _taken_display_orders(session)
    error = _validate_display_order(display_order, taken)
    if error is not None:
        values = {"name_uz": name_uz, "name_ru": name_ru, "display_order": display_order}
        return _form_response(
            request, category=None, values=values, taken=taken, error=error, status_code=400
        )
    session.add(Category(name_uz=name_uz, name_ru=name_ru, display_order=display_order))
    await session.commit()
    return RedirectResponse(url="/categories", status_code=303)


@router.get("/{category_id}/edit")
async def edit_category_form(category_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    category = await catalog_service.get_category(session, category_id)
    if category is None:
        return RedirectResponse(url="/categories", status_code=303)
    taken = await _taken_display_orders(session, exclude_id=category_id)
    values = {
        "name_uz": category.name_uz,
        "name_ru": category.name_ru,
        "display_order": category.display_order,
    }
    return _form_response(request, category=category, values=values, taken=taken)


@router.post("/{category_id}/edit")
async def update_category(
    category_id: int,
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    display_order: int = Form(...),
    session: AsyncSession = Depends(get_db),
):
    category = await catalog_service.get_category(session, category_id)
    if category is None:
        return RedirectResponse(url="/categories", status_code=303)
    taken = await _taken_display_orders(session, exclude_id=category_id)
    error = _validate_display_order(display_order, taken)
    if error is not None:
        values = {"name_uz": name_uz, "name_ru": name_ru, "display_order": display_order}
        return _form_response(
            request, category=category, values=values, taken=taken, error=error, status_code=400
        )
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


@router.post("/{category_id}/delete")
async def delete_category(category_id: int, session: AsyncSession = Depends(get_db)):
    """Hard-delete a category. Refused while active products still point at it;
    products.category_id is ON DELETE RESTRICT, so inactive leftovers block the
    DELETE too — that case is reported rather than left to surface as a 500."""
    category = await catalog_service.get_category(session, category_id)
    if category is None:
        return RedirectResponse(url="/categories", status_code=303)
    linked = (
        await session.execute(select(Product.is_active).where(Product.category_id == category_id))
    ).scalars().all()
    if any(linked):
        return RedirectResponse(url="/categories?error=has_active_products", status_code=303)
    if linked:
        return RedirectResponse(url="/categories?error=has_products", status_code=303)
    try:
        await session.delete(category)
        await session.commit()
    except IntegrityError:
        # a product could have been attached between the check and the commit
        await session.rollback()
        return RedirectResponse(url="/categories?error=has_products", status_code=303)
    return RedirectResponse(url="/categories", status_code=303)
