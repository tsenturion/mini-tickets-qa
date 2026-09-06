import pytest

from quality.support import Client

pytestmark = pytest.mark.api


@pytest.mark.defect("D01")
@pytest.mark.requirement("TICKET-01")
def test_d01_title_81(api):
    response = api.request("POST", "/tickets", json={"title": "x" * 81})
    assert response.status_code == 422


@pytest.mark.defect("D02")
@pytest.mark.requirement("TICKET-02")
def test_d02_unknown_priority(api):
    before = api.request("GET", "/tickets").json()
    response = api.request("POST", "/tickets", json={"title": "Неверный приоритет", "priority": "urgent"})
    assert response.status_code == 422
    assert api.request("GET", "/tickets").json() == before


@pytest.mark.defect("D03")
@pytest.mark.requirement("AUTH-03")
def test_d03_other_owner(api, url):
    ticket = api.create()
    other = Client(url).register()
    assert other.request("GET", f"/tickets/{ticket['id']}").status_code == 404


@pytest.mark.defect("D04")
@pytest.mark.requirement("TICKET-04")
def test_d04_forbidden_transition(api, operator):
    ticket = api.create()
    response = operator.request("PUT", f"/tickets/{ticket['id']}/status", json={"status": "closed"})
    assert response.status_code == 409


@pytest.mark.defect("D05")
@pytest.mark.requirement("TICKET-05")
def test_d05_status_filter(api, operator):
    new = api.create()
    active = api.create()
    assert operator.request("PUT", f"/tickets/{active['id']}/status", json={"status": "active"}).status_code == 200
    response = api.request("GET", "/tickets?status=new")
    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()] == [new["id"]]


@pytest.mark.defect("D06")
@pytest.mark.requirement("COMMENT-01")
def test_d06_comment_author(api, operator):
    ticket = api.create()
    actor = operator.request("GET", "/auth/me").json()
    response = operator.request("POST", f"/tickets/{ticket['id']}/comments", json={"text": "Отвечает оператор"})
    assert response.status_code == 201
    assert response.json()["author_id"] == actor["id"]

