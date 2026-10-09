"""Один сценарий совместимости с метаданными реального браузера и ОС; без автоматических загрузок."""

import argparse
import json
import platform
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def launch_browser(playwright, name):
    """Выбрать установленный брендовый браузер либо подготовленную сборку Playwright."""
    if name in {"chrome", "msedge"}:
        return playwright.chromium.launch(channel=name, headless=True)
    return getattr(playwright, name).launch(headless=True)


def cleanup_session(context, base_url, token, ticket_id, deleted):
    """Отозвать сессию даже при ошибке удаления собственной заявки; вернуть причины неполной очистки."""
    errors = []
    headers = {"Authorization": "Bearer " + token}
    if ticket_id and not deleted:
        try:
            response = context.request.delete(base_url.rstrip("/") + "/api/tickets/" + ticket_id, headers=headers)
            if response.status != 204:
                raise RuntimeError(f"Очистка собственной заявки: HTTP {response.status}")
        except Exception as error:
            errors.append(str(error))
    # Эти действия независимы: неудачное удаление не должно оставлять активную сессию.
    try:
        response = context.request.post(base_url.rstrip("/") + "/api/auth/logout", headers=headers)
        if response.status != 204:
            raise RuntimeError(f"Отзыв браузерной сессии: HTTP {response.status}")
    except Exception as error:
        errors.append(str(error))
    return errors


def check(args):
    """Сравнить данные и доступность действий на собственной новой заявке, затем очистить её и сессию."""
    output = Path(args.output)
    if any((output / name).exists() for name in ("result.json", "card.png", "row.png", "failure-card.png")):
        raise FileExistsError("Доказательства уже существуют: укажите новый --output")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "browser": args.browser,
        "engine": {"firefox": "Gecko", "webkit": "WebKit"}.get(args.browser, "Blink"),
        "host_os": platform.platform(),
        "viewport": {"width": args.width, "height": args.height},
        "mode": "Размер окна настольного браузера; мобильная ОС не эмулируется",
        "base_url": args.base_url,
        "status": "not_run",
    }
    ticket_id = None
    created_record = False
    deleted = False
    page_errors = []
    with sync_playwright() as playwright:
        try:
            browser = launch_browser(playwright, args.browser)
        except Exception as error:
            # Отсутствующий бинарник или невозможность запуска не означают дефект продукта:
            # приложение в этом окружении ещё не открывалось.
            report["status"] = "environment_unavailable"
            report["error"] = str(error).splitlines()[0]
        else:
            report["browser_version"] = browser.version
            context = browser.new_context(viewport=report["viewport"])
            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            try:
                page.goto(args.base_url)
                report["client_parameters"] = page.evaluate("""() => ({
                    user_agent: navigator.userAgent, language: navigator.language,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    pixel_ratio: window.devicePixelRatio, touch_points: navigator.maxTouchPoints
                })""")
                page.get_by_label("Email", exact=True).fill("anna@example.test")
                page.get_by_label("Пароль", exact=True).fill("LabPassword1!")
                page.get_by_role("button", name="Войти", exact=True).click()
                expect(page.get_by_role("table", name="Список заявок")).to_be_visible()
                title = "Совместимость: ё и 🧪 " + uuid.uuid4().hex[:8]
                comment = "Первая строка: ё и 🧪\nВторая строка: русский текст"
                page.get_by_label("Заголовок новой заявки", exact=True).fill(title)
                page.get_by_label("Приоритет новой заявки").select_option("high")
                # Запоминаем ID из ответа до чтения карточки: при поломке UI можно
                # удалить только созданную запись, не перебирая остальные заявки автора.
                with page.expect_response(
                    lambda response: response.request.method == "POST"
                    and urlsplit(response.url).path == "/api/tickets"
                ) as created:
                    page.get_by_role("button", name="Создать заявку", exact=True).click()
                if created.value.status != 201:
                    raise RuntimeError(f"Создание заявки: HTTP {created.value.status}")
                created_record = True
                ticket_id = str(uuid.UUID(created.value.json()["id"]))
                report["ticket_id"] = ticket_id
                expect(page.get_by_role("status")).to_have_text("Заявка создана")
                card = page.get_by_role("complementary", name="Карточка заявки")
                expect(card).to_be_visible()
                row = page.get_by_test_id(f"ticket-{ticket_id}")
                expect(row.get_by_role("button")).to_have_text(title)
                expect(page.get_by_label("Заголовок заявки", exact=True)).to_have_value(title)
                page.get_by_label("Приоритет заявки", exact=True).select_option("low")
                page.get_by_role("button", name="Сохранить изменения", exact=True).click()
                expect(page.get_by_role("status")).to_have_text("Изменения сохранены")
                expect(row.get_by_test_id("ticket-priority")).to_have_text("Низкий")
                page.get_by_label("Комментарий", exact=True).fill(comment)
                page.get_by_role("button", name="Добавить комментарий", exact=True).click()
                expect(page.get_by_role("status")).to_have_text("Комментарий добавлен")
                expect(page.get_by_test_id("comment-text")).to_have_text(comment)
                page.reload()
                expect(row).to_be_visible()
                row.get_by_role("button").click()
                expect(page.get_by_role("button", name="Добавить комментарий", exact=True)).to_be_enabled()
                expect(page.get_by_test_id("comment-text")).to_have_text(comment)
                report["title_preserved"] = page.get_by_label("Заголовок заявки", exact=True).input_value() == title
                # Сравниваем и сырой текст: обычное текстовое ожидание Playwright
                # нормализует пробелы, что могло бы скрыть исчезновение перевода строки.
                report["comment_preserved"] = page.get_by_test_id("comment-text").text_content() == comment
                report["priority_preserved"] = page.get_by_label("Приоритет заявки", exact=True).input_value() == "low"
                report["layout"] = page.evaluate("""() => ({
                    viewport_width: window.innerWidth,
                    document_width: document.documentElement.scrollWidth,
                    grid_columns: getComputedStyle(document.querySelector('.workspace')).gridTemplateColumns,
                    comment_white_space: getComputedStyle(document.querySelector('.comment-text')).whiteSpace
                })""")
                report["page_errors"] = page_errors
                card.screenshot(path=str(output / "card.png"))
                row.screenshot(path=str(output / "row.png"))
                page.get_by_role("button", name="Удалить заявку", exact=True).click()
                expect(page.get_by_role("status")).to_have_text("Заявка удалена")
                expect(row).to_have_count(0)
                deleted = True
                report["own_ticket_deleted"] = True
                page.get_by_role("button", name="Выйти", exact=True).click()
                expect(page.get_by_label("Email", exact=True)).to_be_visible()
                report["logout_confirmed"] = True
                report["status"] = "passed" if (
                    report["title_preserved"] and report["comment_preserved"]
                    and report["priority_preserved"] and not page_errors
                    and report["layout"]["document_width"] <= report["layout"]["viewport_width"] + 1
                ) else "failed"
            except Exception as error:
                report["status"] = "failed"
                report["error"] = str(error)
                card = page.get_by_role("complementary", name="Карточка заявки")
                if card.count() and card.is_visible():
                    card.screenshot(path=str(output / "failure-card.png"))
            finally:
                try:
                    token = page.evaluate("sessionStorage.getItem('lab-token')")
                    if token:
                        cleanup_errors = cleanup_session(context, args.base_url, token, ticket_id, deleted)
                        if cleanup_errors:
                            report["cleanup_error"] = "; ".join(cleanup_errors)
                            report["status"] = "failed"
                except Exception as error:
                    report["cleanup_error"] = str(error)
                    report["status"] = "failed"
                if created_record and ticket_id is None:
                    report["cleanup_error"] = "Создана запись без корректного ID в ответе; адресная очистка невозможна"
                    report["status"] = "failed"
                context.close()
                browser.close()
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    (output / "result.json").write_text(serialized, encoding="utf-8")
    print(serialized)
    return {"passed": 0, "environment_unavailable": 2}.get(report["status"], 1)


def main():
    """Задать локальную цель, браузер и размер окна; результат отражает фактическую ОС запуска."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--browser", choices=("chrome", "msedge", "chromium", "firefox", "webkit"), default="chrome")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    target = urlsplit(args.base_url)
    if target.scheme not in {"http", "https"} or target.hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Используйте адрес собственного локального экземпляра приложения")
    if target.username is not None or target.password is not None:
        parser.error("Учётные данные не должны входить в --base-url")
    if args.width <= 0 or args.height <= 0:
        parser.error("Размер окна должен быть положительным")
    return check(args)


if __name__ == "__main__":
    raise SystemExit(main())
