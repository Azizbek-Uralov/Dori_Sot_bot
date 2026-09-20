from sqlalchemy import select

from app.models.admin import Admin
from tests.conftest import make_admin


async def _fetch_admin(db_session, admin_id: int) -> Admin | None:
    # not session.get(): that answers from the identity map and would hand back
    # an admin row the request under test has already deleted.
    return (
        await db_session.execute(select(Admin).where(Admin.id == admin_id))
    ).scalar_one_or_none()


async def _login(admin_client, db_session, username: str = "admin", password: str = "devpass123") -> Admin:
    admin = await make_admin(db_session, username=username, password=password)
    await db_session.commit()
    await admin_client.post("/login", data={"username": username, "password": password})
    return admin


async def test_admins_list_requires_login(admin_client, db_session):
    response = await admin_client.get("/admins")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


async def test_admins_list_shows_delete_button_with_confirmation(admin_client, db_session):
    await _login(admin_client, db_session)
    other = await make_admin(db_session, username="other", full_name="Other Admin")
    await db_session.commit()

    response = await admin_client.get("/admins")

    assert response.status_code == 200
    assert f'action="/admins/{other.id}/delete"' in response.text
    assert "confirm(" in response.text


async def test_delete_removes_admin_from_db(admin_client, db_session):
    await _login(admin_client, db_session)
    other = await make_admin(db_session, username="other")
    await db_session.commit()

    response = await admin_client.post(f"/admins/{other.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/admins"
    remaining = (await db_session.execute(select(Admin.username))).scalars().all()
    assert remaining == ["admin"]


async def test_delete_works_on_inactive_admin(admin_client, db_session):
    await _login(admin_client, db_session)
    other = await make_admin(db_session, username="retired", is_active=False)
    await db_session.commit()

    response = await admin_client.post(f"/admins/{other.id}/delete")

    assert response.status_code == 303
    assert await _fetch_admin(db_session, other.id) is None


async def test_delete_rejects_last_active_admin(admin_client, db_session):
    # the only active admin is the logged-in one, so deleting it would lock
    # everyone out of the panel for good
    current = await _login(admin_client, db_session)
    await make_admin(db_session, username="retired", is_active=False)
    await db_session.commit()

    response = await admin_client.post(f"/admins/{current.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/admins?error=last_active_admin"
    assert await _fetch_admin(db_session, current.id) is not None


async def test_last_active_admin_error_is_rendered(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.get("/admins", params={"error": "last_active_admin"})

    assert response.status_code == 200
    assert "kamida 1 ta faol admin" in response.text


async def test_delete_rejects_self_even_with_another_active_admin(admin_client, db_session):
    current = await _login(admin_client, db_session)
    await make_admin(db_session, username="colleague", is_active=True)
    await db_session.commit()

    response = await admin_client.post(f"/admins/{current.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/admins?error=self_delete"
    assert await _fetch_admin(db_session, current.id) is not None


async def test_self_delete_error_is_rendered(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.get("/admins", params={"error": "self_delete"})

    assert response.status_code == 200
    assert "o'chira olmaysiz" in response.text


async def test_delete_of_unknown_admin_redirects_without_error(admin_client, db_session):
    await _login(admin_client, db_session)

    response = await admin_client.post("/admins/9999/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/admins"


async def test_delete_requires_login(admin_client, db_session):
    other = await make_admin(db_session, username="other")
    await db_session.commit()

    response = await admin_client.post(f"/admins/{other.id}/delete")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert await _fetch_admin(db_session, other.id) is not None
