from sqlalchemy import select

from app.models.category import Category
from tests.conftest import make_admin, make_category, make_product


async def _login(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()
    await admin_client.post("/login", data={"username": "admin", "password": "devpass123"})


async def _fetch_category(db_session, category_id: int) -> Category | None:
    # not session.get(): that answers from the identity map and would hand back
    # a category row the request under test has already deleted.
    return (
        await db_session.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()


async def test_categories_list_requires_login(admin_client, db_session):
    response = await admin_client.get("/categories")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


async def test_new_form_lists_taken_display_orders(admin_client, db_session):
    await _login(admin_client, db_session)
    await make_category(db_session, name_uz="Birinchi", display_order=1)
    await make_category(db_session, name_uz="Ikkinchi", display_order=3)
    await db_session.commit()

    response = await admin_client.get("/categories/new")

    assert response.status_code == 200
    assert "Band bo'lgan raqamlar: 1, 3" in response.text
    # the pre-filled suggestion must itself be free
    assert 'name="display_order" value="4"' in response.text


async def test_new_form_input_enforces_minimum_of_one(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.get("/categories/new")

    assert response.status_code == 200
    assert 'min="1"' in response.text


async def test_create_category_with_free_display_order(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.post(
        "/categories/new",
        data={"name_uz": "Vitaminlar", "name_ru": "Витамины", "display_order": "2"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/categories"
    category = (
        await db_session.execute(select(Category).where(Category.name_uz == "Vitaminlar"))
    ).scalar_one()
    assert category.display_order == 2


async def test_create_rejects_zero_display_order(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.post(
        "/categories/new",
        data={"name_uz": "Vitaminlar", "name_ru": "Витамины", "display_order": "0"},
    )

    assert response.status_code == 400
    assert "musbat butun son" in response.text
    # the typed-in names survive the re-render
    assert 'value="Vitaminlar"' in response.text
    assert (await db_session.execute(select(Category))).scalars().all() == []


async def test_create_rejects_negative_display_order(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.post(
        "/categories/new",
        data={"name_uz": "Vitaminlar", "name_ru": "Витамины", "display_order": "-3"},
    )

    assert response.status_code == 400
    assert "musbat butun son" in response.text
    assert (await db_session.execute(select(Category))).scalars().all() == []


async def test_create_rejects_taken_display_order(admin_client, db_session):
    await _login(admin_client, db_session)
    await make_category(db_session, name_uz="Birinchi", display_order=1)
    await db_session.commit()

    response = await admin_client.post(
        "/categories/new",
        data={"name_uz": "Ikkinchi", "name_ru": "Второй", "display_order": "1"},
    )

    assert response.status_code == 400
    assert "Bu tartib raqam allaqachon band" in response.text
    names = (await db_session.execute(select(Category.name_uz))).scalars().all()
    assert names == ["Birinchi"]


async def test_edit_does_not_treat_own_display_order_as_taken(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session, name_uz="Birinchi", display_order=1)
    await db_session.commit()

    response = await admin_client.post(
        f"/categories/{category.id}/edit",
        data={"name_uz": "Birinchi (yangi)", "name_ru": "Первый", "display_order": "1"},
    )

    assert response.status_code == 303
    await db_session.refresh(category)
    assert category.name_uz == "Birinchi (yangi)"
    assert category.display_order == 1


async def test_edit_form_excludes_own_display_order_from_hint(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session, name_uz="Birinchi", display_order=1)
    await make_category(db_session, name_uz="Ikkinchi", display_order=2)
    await db_session.commit()

    response = await admin_client.get(f"/categories/{category.id}/edit")

    assert response.status_code == 200
    assert "Band bo'lgan raqamlar: 2" in response.text


async def test_edit_rejects_display_order_taken_by_another_category(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session, name_uz="Birinchi", display_order=1)
    await make_category(db_session, name_uz="Ikkinchi", display_order=2)
    await db_session.commit()

    response = await admin_client.post(
        f"/categories/{category.id}/edit",
        data={"name_uz": "Birinchi", "name_ru": "Первый", "display_order": "2"},
    )

    assert response.status_code == 400
    assert "Bu tartib raqam allaqachon band" in response.text
    await db_session.refresh(category)
    assert category.display_order == 1


async def test_edit_rejects_zero_display_order(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session, name_uz="Birinchi", display_order=1)
    await db_session.commit()

    response = await admin_client.post(
        f"/categories/{category.id}/edit",
        data={"name_uz": "Birinchi", "name_ru": "Первый", "display_order": "0"},
    )

    assert response.status_code == 400
    await db_session.refresh(category)
    assert category.display_order == 1


async def test_list_shows_delete_button_with_confirmation(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session, display_order=1)
    await db_session.commit()

    response = await admin_client.get("/categories")

    assert response.status_code == 200
    assert f'action="/categories/{category.id}/delete"' in response.text
    assert "confirm(" in response.text


async def test_delete_removes_empty_category(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session, display_order=1)
    await db_session.commit()

    response = await admin_client.post(f"/categories/{category.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/categories"
    assert await _fetch_category(db_session, category.id) is None


async def test_delete_rejected_when_category_has_active_products(admin_client, db_session):
    await _login(admin_client, db_session)
    category = await make_category(db_session, display_order=1)
    await make_product(db_session, category=category, is_active=True)
    await db_session.commit()

    response = await admin_client.post(f"/categories/{category.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/categories?error=has_active_products"
    assert await _fetch_category(db_session, category.id) is not None


async def test_active_products_error_is_rendered(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.get("/categories", params={"error": "has_active_products"})

    assert response.status_code == 200
    assert "faol mahsulotlar mavjud" in response.text


async def test_delete_rejected_when_category_has_inactive_products(admin_client, db_session):
    # products.category_id is ON DELETE RESTRICT, so even a deactivated product
    # keeps the category alive — that has to read as an error page, not a 500.
    await _login(admin_client, db_session)
    category = await make_category(db_session, display_order=1)
    await make_product(db_session, category=category, is_active=False)
    await db_session.commit()

    response = await admin_client.post(f"/categories/{category.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/categories?error=has_products"
    assert await _fetch_category(db_session, category.id) is not None


async def test_delete_of_unknown_category_redirects_without_error(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.post("/categories/9999/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/categories"


async def test_delete_requires_login(admin_client, db_session):
    category = await make_category(db_session, display_order=1)
    await db_session.commit()

    response = await admin_client.post(f"/categories/{category.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert await _fetch_category(db_session, category.id) is not None
