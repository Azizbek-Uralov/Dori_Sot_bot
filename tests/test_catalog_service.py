from app.services import catalog_service
from tests.conftest import make_category, make_product


def test_is_purchasable_true_when_active_and_in_stock():
    from app.models.product import Product

    product = Product(category_id=1, name_uz="x", name_ru="x", price=1000, stock_quantity=5, is_active=True)
    assert product.is_purchasable is True


def test_is_purchasable_false_when_inactive():
    from app.models.product import Product

    product = Product(category_id=1, name_uz="x", name_ru="x", price=1000, stock_quantity=5, is_active=False)
    assert product.is_purchasable is False


def test_is_purchasable_false_when_out_of_stock():
    from app.models.product import Product

    product = Product(category_id=1, name_uz="x", name_ru="x", price=1000, stock_quantity=0, is_active=True)
    assert product.is_purchasable is False


async def test_list_products_excludes_inactive_by_default(db_session):
    category = await make_category(db_session)
    active = await make_product(db_session, category=category, name_uz="active", is_active=True)
    await make_product(db_session, category=category, name_uz="inactive", is_active=False)

    products = await catalog_service.list_products(db_session, category.id)

    assert [p.id for p in products] == [active.id]


async def test_list_products_includes_inactive_when_requested(db_session):
    category = await make_category(db_session)
    await make_product(db_session, category=category, name_uz="active", is_active=True)
    await make_product(db_session, category=category, name_uz="inactive", is_active=False)

    products = await catalog_service.list_products(db_session, category.id, active_only=False)

    assert len(products) == 2


async def test_list_categories_excludes_inactive_by_default(db_session):
    await make_category(db_session, name_uz="visible", is_active=True)
    await make_category(db_session, name_uz="hidden", is_active=False)

    categories = await catalog_service.list_categories(db_session)

    assert [c.name_uz for c in categories] == ["visible"]
