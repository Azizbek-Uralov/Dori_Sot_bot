from admin.auth import hash_password, verify_password
from tests.conftest import make_admin


def test_verify_password_rejects_input_over_72_bytes():
    # bcrypt itself raises ValueError past 72 bytes instead of just failing
    # the check; verify_password must treat that as "wrong password" rather
    # than letting the error escape to the caller.
    password_hash = hash_password("devpass123")

    assert verify_password("a" * 73, password_hash) is False


def test_verify_password_counts_utf8_bytes_not_characters():
    # multi-byte characters can push the byte length over 72 well before the
    # character count does, so the check must be on encoded bytes.
    password_hash = hash_password("devpass123")

    assert len("ў" * 40) == 40
    assert len(("ў" * 40).encode("utf-8")) > 72
    assert verify_password("ў" * 40, password_hash) is False


def test_verify_password_still_accepts_correct_password_at_the_boundary():
    password = "a" * 72
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


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


async def test_login_with_overlong_password_rejected(admin_client, db_session):
    await make_admin(db_session, username="admin", password="devpass123")
    await db_session.commit()

    response = await admin_client.post(
        "/login", data={"username": "admin", "password": "a" * 100}
    )

    assert response.status_code == 401
    assert "session" not in response.cookies
    assert "Login yoki parol noto" in response.text


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
