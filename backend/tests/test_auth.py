def test_login_and_current_user(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "elisa", "password": "qwerty123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "elisa"
    assert data["user"]["crew_member_code"] == "elisa"
    assert data["access_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["full_name"] == "Elisa"


def test_invalid_credentials_are_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "elisa", "password": "incorrect"},
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/api/crew", headers={"Authorization": ""})
    assert response.status_code == 401


def test_crew_member_cannot_use_another_profile(client):
    login = client.post(
        "/api/auth/login",
        json={"username": "elisa", "password": "qwerty123"},
    ).json()
    response = client.post(
        "/api/care/evaluate",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"crew_member_code": "elsa", "symptoms": ["mal de tete"]},
    )
    assert response.status_code == 403
