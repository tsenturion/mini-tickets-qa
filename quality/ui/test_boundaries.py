import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.ui


@pytest.mark.requirement("TICKET-01")
@pytest.mark.requirement("COMMENT-01")
def test_unicode_boundaries_match_api(logged_page, api):
    title, comment = "🧪" * 80, "🧪" * 300
    logged_page.get_by_label("Заголовок новой заявки", exact=True).fill(" " + title + " ")
    logged_page.get_by_role("button", name="Создать заявку", exact=True).click()
    expect(logged_page.get_by_role("status")).to_have_text("Заявка создана")
    created = api.request("GET", "/tickets").json()[0]
    assert created["title"] == title
    logged_page.get_by_label("Комментарий", exact=True).fill(comment)
    logged_page.get_by_role("button", name="Добавить комментарий", exact=True).click()
    expect(logged_page.get_by_test_id("comment-text")).to_have_text(comment)


@pytest.mark.requirement("AUTH-01")
def test_unicode_password_registration(page, url):
    import uuid
    import requests

    email = f"unicode-{uuid.uuid4().hex}@example.test"
    page.goto(url)
    page.get_by_role("button", name="Создать аккаунт", exact=True).click()
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Пароль", exact=True).fill("🧪" * 64)
    page.get_by_role("button", name="Зарегистрироваться", exact=True).click()
    expect(page.get_by_role("heading", name="Заявки")).to_be_visible()
    response = requests.post(url + "/api/auth/login", json={"email": email, "password": "🧪" * 64}, timeout=10)
    assert response.status_code == 200
