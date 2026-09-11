from pathlib import Path

import pytest
from sqlalchemy import select

from admin.uploads import UPLOAD_DIR
from app.models.product import Product
from tests.conftest import make_admin, make_category, make_product


@pytest.fixture(autouse=True)
def _cleanup_uploads():
    yield
    if UPLOAD_DIR.exists():
        for path in UPLOAD_DIR.iterdir():
            if path.name != ".gitkeep":
                path.unlink()


async def _login(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()
    await admin_client.post("/login", data={"username": "admin", "password": "devpass123"})


async def test_products_list_requires_login(admin_client, db_session):
    response = await admin_client.get("/products")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


async def test_products_list_renders_for_logged_in_admin(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.get("/products")

    assert response.status_code == 200


async def test_create_product_without_image(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session)
    await db_session.commit()

    response = await admin_client.post(
        "/products/new",
        data={
            "name_uz": "Vitamin B",
            "name_ru": "Витамин B",
            "description_uz": "",
            "description_ru": "",
            "price": "35000",
            "category_id": str(category.id),
            "stock_quantity": "5",
        },
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/products"

    product = (
        await db_session.execute(select(Product).where(Product.name_uz == "Vitamin B"))
    ).scalar_one()
    assert product.price == 35000
    assert product.stock_quantity == 5
    assert product.category_id == category.id
    assert product.image_path is None


async def test_create_product_with_image_upload(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session)
    await db_session.commit()

    response = await admin_client.post(
        "/products/new",
        data={
            "name_uz": "Vitamin C",
            "name_ru": "Витамин C",
            "description_uz": "",
            "description_ru": "",
            "price": "40000",
            "category_id": str(category.id),
            "stock_quantity": "3",
        },
        files={"image": ("product.png", b"\x89PNG-fake-bytes", "image/png")},
    )

    assert response.status_code == 303

    product = (
        await db_session.execute(select(Product).where(Product.name_uz == "Vitamin C"))
    ).scalar_one()
    assert product.image_path is not None
    assert Path(product.image_path).exists()
    assert Path(product.image_path).suffix == ".png"


async def test_edit_product_updates_fields(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, name_uz="Old name", price=10000)
    await db_session.commit()

    response = await admin_client.post(
        f"/products/{product.id}/edit",
        data={
            "name_uz": "New name",
            "name_ru": "Новое имя",
            "description_uz": "",
            "description_ru": "",
            "price": "99000",
            "category_id": str(category.id),
            "stock_quantity": "7",
        },
    )

    assert response.status_code == 303
    await db_session.refresh(product)
    assert product.name_uz == "New name"
    assert product.price == 99000
    assert product.stock_quantity == 7


async def test_toggle_active_flips_flag(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session)
    product = await make_product(db_session, category=category, is_active=True)
    await db_session.commit()

    response = await admin_client.post(f"/products/{product.id}/toggle-active")

    assert response.status_code == 303
    await db_session.refresh(product)
    assert product.is_active is False

    await admin_client.post(f"/products/{product.id}/toggle-active")
    await db_session.refresh(product)
    assert product.is_active is True
