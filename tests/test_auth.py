from scenemaker.seed import DEMO_TENANT_SLUG


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_login_and_me(client, auth):
    me = client.get("/auth/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"
    assert me.json()["credits"] == 0

    login = client.post(
        "/auth/login",
        json={
            "tenant_slug": DEMO_TENANT_SLUG,
            "email": "Ada@Example.com",
            "password": "correct horse",
        },
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_duplicate_email_in_same_tenant_rejected(client, register):
    register()
    response = client.post(
        "/auth/register",
        json={
            "tenant_slug": DEMO_TENANT_SLUG,
            "email": "ada@example.com",
            "password": "correct horse",
        },
    )
    assert response.status_code == 409


def test_unknown_tenant_rejected(client):
    response = client.post(
        "/auth/register",
        json={"tenant_slug": "nope", "email": "x@example.com", "password": "correct horse"},
    )
    assert response.status_code == 404


def test_wrong_password_rejected(client, register):
    register()
    response = client.post(
        "/auth/login",
        json={
            "tenant_slug": DEMO_TENANT_SLUG,
            "email": "ada@example.com",
            "password": "wrong password",
        },
    )
    assert response.status_code == 401


def test_protected_routes_require_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/templates").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401
