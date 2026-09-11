from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from admin.deps import get_current_admin, get_db
from admin.uploads import delete_product_image, save_product_image
from app.models.product import Product
from app.services import catalog_service

router = APIRouter(prefix="/products", dependencies=[Depends(get_current_admin)])
templates = Jinja2Templates(directory="templates")


@router.get("")
async def list_products(
    request: Request,
    category_id: int | None = None,
    session: AsyncSession = Depends(get_db),
):
    categories = await catalog_service.list_categories(session, active_only=False)
    if category_id:
        products = await catalog_service.list_products(session, category_id, active_only=False)
    else:
        products = []
        for category in categories:
            products += await catalog_service.list_products(session, category.id, active_only=False)
    return templates.TemplateResponse(
        request,
        "products/list.html",
        {"products": products, "categories": categories, "selected_category_id": category_id},
    )


@router.get("/new")
async def new_product_form(request: Request, session: AsyncSession = Depends(get_db)):
    categories = await catalog_service.list_categories(session, active_only=False)
    return templates.TemplateResponse(request, "products/form.html", {"product": None, "categories": categories})


@router.post("/new")
async def create_product(
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    description_uz: str = Form(""),
    description_ru: str = Form(""),
    price: int = Form(...),
    category_id: int = Form(...),
    stock_quantity: int = Form(0),
    image: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
):
    image_path = None
    if image is not None and image.filename:
        image_path = await save_product_image(image)
    product = Product(
        name_uz=name_uz,
        name_ru=name_ru,
        description_uz=description_uz or None,
        description_ru=description_ru or None,
        price=price,
        category_id=category_id,
        stock_quantity=stock_quantity,
        image_path=image_path,
    )
    session.add(product)
    await session.commit()
    return RedirectResponse(url="/products", status_code=303)


@router.get("/{product_id}/edit")
async def edit_product_form(product_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    product = await catalog_service.get_product(session, product_id)
    categories = await catalog_service.list_categories(session, active_only=False)
    return templates.TemplateResponse(
        request, "products/form.html", {"product": product, "categories": categories}
    )


@router.post("/{product_id}/edit")
async def update_product(
    product_id: int,
    request: Request,
    name_uz: str = Form(...),
    name_ru: str = Form(...),
    description_uz: str = Form(""),
    description_ru: str = Form(""),
    price: int = Form(...),
    category_id: int = Form(...),
    stock_quantity: int = Form(0),
    image: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
):
    product = await catalog_service.get_product(session, product_id)
    if product is not None:
        product.name_uz = name_uz
        product.name_ru = name_ru
        product.description_uz = description_uz or None
        product.description_ru = description_ru or None
        product.price = price
        product.category_id = category_id
        product.stock_quantity = stock_quantity
        if image is not None and image.filename:
            old_path = product.image_path
            product.image_path = await save_product_image(image)
            delete_product_image(old_path)
        await session.commit()
    return RedirectResponse(url="/products", status_code=303)


@router.post("/{product_id}/toggle-active")
async def toggle_product_active(product_id: int, session: AsyncSession = Depends(get_db)):
    product = await catalog_service.get_product(session, product_id)
    if product is not None:
        product.is_active = not product.is_active
        await session.commit()
    return RedirectResponse(url="/products", status_code=303)
