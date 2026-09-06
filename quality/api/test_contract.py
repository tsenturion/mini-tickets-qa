import uuid

import pytest

from quality.support import Client

pytestmark = pytest.mark.api


@pytest.mark.requirement("AUTH-01")
def test_register_normalization_and_duplicates(url):
    email = f"Dup-{uuid.uuid4().hex}@Example.Test"
    client = Client(url)
    body = {"email": email, "password": "12345678"}
    first = client.request("POST", "/auth/register", json=body)
    assert first.status_code == 201
    assert first.json()["email"] == email.lower()
    assert "password_hash" not in first.json()
    assert client.request("POST", "/auth/register", json=body).status_code == 409
    body["email"] = "other-" + email
    body["role"] = "operator"
    assert client.request("POST", "/auth/register", json=body).status_code == 422


@pytest.mark.requirement("AUTH-02")
def test_logout_revokes_token(api):
    assert api.request("GET", "/auth/me").status_code == 200
    assert api.request("POST", "/auth/logout").status_code == 204
    assert api.request("GET", "/auth/me").status_code == 401


@pytest.mark.parametrize("token", [None, "Bearer wrong", "Basic YTpi"])
def test_auth_required(url, token):
    client = Client(url)
    if token:
        client.session.headers["Authorization"] = token
    response = client.request("GET", "/tickets")
    assert response.status_code == 401


@pytest.mark.requirement("TICKET-01")
@pytest.mark.parametrize("length,expected", [(2, 422), (3, 201), (80, 201)])
def test_title_boundaries(api, length, expected):
    response = api.request("POST", "/tickets", json={"title": "a" * length})
    assert response.status_code == expected


def test_crud_and_comments(api):
    ticket = api.create("  Проверка CRUD  ")
    path = f"/tickets/{ticket['id']}"
    assert ticket["title"] == "Проверка CRUD"
    assert ticket["status"] == "new" and ticket["priority"] == "normal"
    assert api.request("GET", path).json() == ticket
    updated = api.request("PATCH", path, json={"priority": "high"})
    assert updated.status_code == 200 and updated.json()["priority"] == "high"
    comment = api.request("POST", path + "/comments", json={"text": "  Комментарий  "})
    assert comment.status_code == 201 and comment.json()["text"] == "Комментарий"
    assert len(api.request("GET", path + "/comments").json()) == 1
    assert api.request("DELETE", path).status_code == 204
    assert api.request("GET", path).status_code == 404


def test_status_lifecycle(api, operator):
    ticket = api.create()
    path = f"/tickets/{ticket['id']}"
    assert api.request("PUT", path + "/status", json={"status": "active"}).status_code == 403
    for state in ["active", "active", "closed"]:
        assert operator.request("PUT", path + "/status", json={"status": state}).status_code == 200
    assert api.request("POST", path + "/comments", json={"text": "Поздно"}).status_code == 409
    assert api.request("PATCH", path, json={"title": "Нельзя"}).status_code == 409
    assert api.request("DELETE", path).status_code == 409
    assert operator.request("PUT", path + "/status", json={"status": "active"}).status_code == 200


def test_unknown_fields_null_empty_patch_and_missing(api):
    ticket = api.create()
    path = f"/tickets/{ticket['id']}"
    for body in [{}, {"title": None}, {"author_id": api.user["id"]}, {"status": "closed"}]:
        assert api.request("PATCH", path, json=body).status_code == 422
    assert api.request("GET", f"/tickets/{uuid.uuid4()}").status_code == 404
    assert api.request("GET", "/tickets?status=wrong").status_code == 422


def test_sql_like_input_and_request_correlation(api):
    ticket = api.create("'; DROP TABLE users; --")
    response = api.request("GET", f"/tickets/{ticket['id']}", headers={"X-Request-ID": "course-test-01"})
    assert response.status_code == 200
    assert response.json()["title"] == "'; DROP TABLE users; --"
    assert response.headers["X-Request-ID"] == "course-test-01"
    assert api.request("GET", "/auth/me").status_code == 200

