"""Проверить безопасный вывод сохранённых маркеров в установленном Chrome и сохранить доказательства."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from playwright.sync_api import expect, sync_playwright

TITLE_PAYLOAD = '<svg onload="window.__qaTitleXss=1"></svg>'
COMMENT_PAYLOAD = '<svg onload="window.__qaCommentXss=1"></svg>'


def inspect_ticket(page, ticket_id):
    """Проверить буквальный текст, отсутствие внедрённых SVG и несработавшие обработчики."""
    expect(page.get_by_role("table", name="Список заявок")).to_be_visible()
    row = page.get_by_test_id(f"ticket-{ticket_id}")
    title = row.get_by_role("button", name=TITLE_PAYLOAD, exact=True)
    expect(title).to_have_text(TITLE_PAYLOAD)
    title.click()
    comment = page.get_by_test_id("comment-text")
    expect(comment).to_have_text(COMMENT_PAYLOAD)
    return {
        "title_is_literal": title.text_content() == TITLE_PAYLOAD,
        "comment_is_literal": comment.text_content() == COMMENT_PAYLOAD,
        "title_svg_count": row.locator("svg").count(),
        "comment_svg_count": comment.locator("svg").count(),
        "title_marker": page.evaluate("window.__qaTitleXss"),
        "comment_marker": page.evaluate("window.__qaCommentXss"),
    }


def safe_display(result):
    """Связать успешный результат с наблюдаемым DOM, а не только с отсутствием всплывающего окна."""
    return (
        result["title_is_literal"]
        and result["comment_is_literal"]
        and result["title_svg_count"] == 0
        and result["comment_svg_count"] == 0
        and result["title_marker"] == 0
        and result["comment_marker"] == 0
    )


def verify(args):
    """Проверить чужую автору страницу под оператором; не изменять заявки или настройки продукта."""
    output = Path(args.output)
    if any((output / name).exists() for name in ("xss-check.json", "xss-card.png", "xss-title.png", "xss-failure.png")):
        raise FileExistsError("В каталоге уже есть доказательства: укажите новый --output")
    output.mkdir(parents=True, exist_ok=True)
    report = {"base_url": args.base_url, "ticket_id": str(args.ticket_id), "passed": False}
    page_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.browser_channel, headless=True)
        context = browser.new_context(viewport={"width": 1365, "height": 1000})
        # Маркеры заново инициализируются при загрузке, чтобы проверить первое открытие
        # и повторное чтение сохранённых данных после перезагрузки страницы.
        context.add_init_script("window.__qaTitleXss=0; window.__qaCommentXss=0;")
        page = context.new_page()
        authenticated = False
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        try:
            # Контроль исполняется в отдельном документе без входа и серверных данных.
            # Оба обработчика только меняют числа в window: нет внешних запросов или чтения секретов.
            control = context.new_page()
            control.set_content("<!doctype html><html><body>" + TITLE_PAYLOAD + COMMENT_PAYLOAD + "</body></html>")
            control.wait_for_function("window.__qaTitleXss===1 && window.__qaCommentXss===1")
            report["positive_control"] = True
            control.close()

            page.goto(args.base_url)
            page.get_by_label("Email", exact=True).fill("operator@example.test")
            page.get_by_label("Пароль", exact=True).fill("LabPassword1!")
            page.get_by_role("button", name="Войти", exact=True).click()
            expect(page.get_by_role("table", name="Список заявок")).to_be_visible()
            authenticated = True
            report["first_open"] = inspect_ticket(page, args.ticket_id)
            page.reload()
            report["after_reload"] = inspect_ticket(page, args.ticket_id)
            # Сохраняем только подготовленную карточку и её строку, без остальных данных оператора.
            page.get_by_role("complementary", name="Карточка заявки").screenshot(path=str(output / "xss-card.png"))
            page.get_by_test_id(f"ticket-{args.ticket_id}").screenshot(path=str(output / "xss-title.png"))
            report["passed"] = safe_display(report["first_open"]) and safe_display(report["after_reload"]) and not page_errors
        except Exception as error:
            report["error"] = str(error)
            if not page.is_closed():
                card = page.get_by_role("complementary", name="Карточка заявки")
                if card.count() and card.is_visible():
                    card.screenshot(path=str(output / "xss-failure.png"))
        finally:
            # Выходим штатной кнопкой; при сломанном UI пробуем отозвать сохранённый
            # токен прямо через API. Секрет в обоих случаях не входит в доказательства.
            try:
                logout = page.get_by_role("button", name="Выйти", exact=True)
                if logout.count():
                    logout.click()
                    expect(page.get_by_label("Email", exact=True)).to_be_visible()
                    report["logout_confirmed"] = True
                else:
                    token = page.evaluate("sessionStorage.getItem('lab-token')")
                    if token:
                        response = context.request.post(
                            args.base_url.rstrip("/") + "/api/auth/logout",
                            headers={"Authorization": "Bearer " + token},
                            timeout=10000,
                        )
                        if response.status != 204:
                            raise RuntimeError(f"Отзыв браузерной сессии: HTTP {response.status}")
                        report["logout_confirmed"] = True
                    elif authenticated:
                        raise RuntimeError("Отзыв браузерной сессии не подтверждён")
            except Exception as error:
                report["cleanup_error"] = str(error)
                report["passed"] = False
            report["page_errors"] = page_errors
            context.close()
            browser.close()
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    (output / "xss-check.json").write_text(serialized, encoding="utf-8")
    print(serialized)
    return 0 if report["passed"] else 1


def main():
    """Принять адрес локальной среды и ID подготовленной заявки; браузеры автоматически не скачивать."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--ticket-id", required=True, type=UUID)
    parser.add_argument("--output", default=".runtime/security-results/xss")
    parser.add_argument("--browser-channel", default="chrome")
    args = parser.parse_args()
    target = urlsplit(args.base_url)
    # Учебный запуск предназначен для собственного localhost. Проверяем адрес до
    # открытия формы, чтобы ошибочный URL не получил введённый учебный пароль.
    if target.scheme not in {"http", "https"} or target.hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Используйте адрес собственной локальной среды localhost, 127.0.0.1 или ::1")
    if target.username is not None or target.password is not None:
        parser.error("Учётные данные не должны входить в --base-url")
    return verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
