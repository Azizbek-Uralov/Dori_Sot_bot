from tests.conftest import make_admin


async def test_login_page_renders(admin_client, db_session):
    response = await admin_client.get("/login")
    assert response.status_code == 200


async def test_root_redirects_to_login_when_unauthenticated(admin_client, db_session):
    response = await admin_client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


async def test_login_with_correct_credentials_succeeds(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()

    response = await admin_client.post("/login", data={"username": "admin", "password": "devpass123"})

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "session" in response.cookies


async def test_authenticated_session_can_reach_dashboard(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()
    await admin_client.post("/login", data={"username": "admin", "password": "devpass123"})

    response = await admin_client.get("/")

    assert response.status_code == 200


async def test_login_with_wrong_password_rejected(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()

    response = await admin_client.post("/login", data={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
    assert "session" not in response.cookies


async def test_login_with_unknown_username_rejected(admin_client, db_session):
    response = await admin_client.post("/login", data={"username": "ghost", "password": "whatever"})

    assert response.status_code == 401


async def test_login_rejects_inactive_admin(admin_client, db_session):
    await make_admin(db_session, username="disabled", password="devpass123", is_active=False)
    await db_session.commit()

    response = await admin_client.post("/login", data={"username": "disabled", "password": "devpass123"})

    assert response.status_code == 401


async def test_logout_clears_session(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()
    await admin_client.post("/login", data={"username": "admin", "password": "devpass123"})

    logout_response = await admin_client.post("/logout")
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"

    response = await admin_client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
