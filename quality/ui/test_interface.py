import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.ui


@pytest.mark.requirement("UI-01")
def test_create_and_delete(logged_page):
    page = logged_page
    page.get_by_label("Заголовок новой заявки", exact=True).fill("Проверка через интерфейс")
    page.get_by_role("button", name="Создать заявку", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Заявка создана")
    expect(page.get_by_role("table")).to_contain_text("Проверка через интерфейс")
    page.get_by_role("button", name="Удалить заявку", exact=True).click()
    expect(page.get_by_role("table")).not_to_contain_text("Проверка через интерфейс")


@pytest.mark.defect("D07")
@pytest.mark.requirement("UI-02")
def test_d07_priority_refresh(logged_page, api):
    ticket = api.create("Приоритет в списке")
    page = logged_page
    page.reload()
    row = page.get_by_test_id(f"ticket-{ticket['id']}")
    row.get_by_role("button").click()
    page.get_by_label("Приоритет заявки", exact=True).select_option("high")
    page.get_by_role("button", name="Сохранить изменения", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Изменения сохранены")
    expect(row.get_by_test_id("ticket-priority")).to_have_text("Высокий")


@pytest.mark.defect("D08")
@pytest.mark.requirement("UI-03")
def test_d08_comment_is_plain_text(logged_page, api):
    ticket = api.create("Безопасное отображение")
    payload = '<b data-probe="injection">учебный текст</b>'
    assert api.request("POST", f"/tickets/{ticket['id']}/comments", json={"text": payload}).status_code == 201
    page = logged_page
    page.reload()
    page.get_by_test_id(f"ticket-{ticket['id']}").get_by_role("button").click()
    expect(page.get_by_test_id("comment-text")).to_have_text(payload)
    expect(page.locator('[data-probe="injection"]')).to_have_count(0)

