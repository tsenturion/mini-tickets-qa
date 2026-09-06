import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage


@pytest.mark.ui
@pytest.mark.requirement("UI-01")
def test_login_screen(page, url):
    LoginPage(page).open(url)
    expect(page.get_by_role("heading", name="Вход в систему")).to_be_visible()

