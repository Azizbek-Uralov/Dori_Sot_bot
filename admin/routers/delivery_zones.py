from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from app.models.delivery_zone import DeliveryZone
from app.services import delivery_service

router = APIRouter(prefix="/zones", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


def _parse_threshold(raw: str) -> int | None:
    raw = raw.strip()
    return int(raw) if raw else None


@router.get("")
async def list_zones(request: Request, session: AsyncSession = Depends(get_db)):
    zones = await delivery_service.list_zones(session, active_only=False)
    return templates.TemplateResponse(request, "delivery_zones/list.html", {"zones": zones})


@router.get("/new")
async def new_zone_form(request: Request):
    return templates.TemplateResponse(request, "delivery_zones/form.html", {"zone": None})


@router.post("/new")
async def create_zone(
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    delivery_price: int = Form(...),
    free_delivery_threshold: str = Form(""),
    display_order: int = Form(0),
    session: AsyncSession = Depends(get_db),
):
    session.add(
        DeliveryZone(
            name_uz=name_uz,
            name_ru=name_ru,
            delivery_price=delivery_price,
            free_delivery_threshold=_parse_threshold(free_delivery_threshold),
            display_order=display_order,
        )
    )
    await session.commit()
    return RedirectResponse(url="/zones", status_code=303)


@router.get("/{zone_id}/edit")
async def edit_zone_form(zone_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    zone = await delivery_service.get_zone(session, zone_id)
    return templates.TemplateResponse(request, "delivery_zones/form.html", {"zone": zone})


@router.post("/{zone_id}/edit")
async def update_zone(
    zone_id: int,
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    delivery_price: int = Form(...),
    free_delivery_threshold: str = Form(""),
    display_order: int = Form(0),
    session: AsyncSession = Depends(get_db),
):
    zone = await delivery_service.get_zone(session, zone_id)
    if zone is not None:
        zone.name_uz = name_uz
        zone.name_ru = name_ru
        zone.delivery_price = delivery_price
        zone.free_delivery_threshold = _parse_threshold(free_delivery_threshold)
        zone.display_order = display_order
        await session.commit()
    return RedirectResponse(url="/zones", status_code=303)


@router.post("/{zone_id}/toggle-active")
async def toggle_zone_active(zone_id: int, session: AsyncSession = Depends(get_db)):
    zone = await delivery_service.get_zone(session, zone_id)
    if zone is not None:
        zone.is_active = not zone.is_active
        await session.commit()
    return RedirectResponse(url="/zones", status_code=303)
