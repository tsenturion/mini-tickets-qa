"""Показать на реальном UI разницу между мгновенным чтением и ожиданием Playwright."""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.logging_setup import configure

EMAIL = "anna@example.test"
PASSWORD = "LabPassword1!"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
log = configure(ROOT / "logs" / "waits", "waits")


def require_status(response, expected, operation):
    """Проверить HTTP-статус, не добавляя тело ответа и секреты в ошибку."""
    if response.status_code != expected:
        raise RuntimeError(f"{operation}: ожидался HTTP {expected}, получен HTTP {response.status_code}")


def api_setup(session, base_url, title):
    """Открыть отдельную API-сессию и создать ровно одну заявку для сценария."""
    login = session.post(
        f"{base_url}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=10,
    )
    require_status(login, 200, "Вход через API")
    token = login.json()["access_token"]
    session.headers["Authorization"] = f"Bearer {token}"
    created = session.post(
        f"{base_url}/api/tickets",
        json={"title": title, "priority": "normal"},
        timeout=10,
    )
    require_status(created, 201, "Создание заявки")
    ticket_id = str(uuid.UUID(created.json()["id"]))
    return token, ticket_id


def revoke_session(session, base_url, token, label):
    """Отозвать одну предъявленную сессию и подтвердить её недействительность."""
    headers = {"Authorization": f"Bearer {token}"}
    response = session.post(f"{base_url}/api/auth/logout", headers=headers, timeout=10)
    require_status(response, 204, f"Отзыв сессии {label}")
    check = session.get(f"{base_url}/api/auth/me", headers=headers, timeout=10)
    require_status(check, 401, f"Проверка отзыва сессии {label}")
    log.info("Сессия отозвана", extra={"fields": {"session_kind": label}})


def cleanup(session, base_url, api_token, browser_token, ticket_id):
    """Удалить только созданную сценарием заявку и независимо отозвать обе сессии."""
    errors = []
    api_headers = {"Authorization": f"Bearer {api_token}"} if api_token else None
    if ticket_id and api_headers:
        try:
            deleted = session.delete(f"{base_url}/api/tickets/{ticket_id}", headers=api_headers, timeout=10)
            require_status(deleted, 204, "Удаление собственной заявки")
            absent = session.get(f"{base_url}/api/tickets/{ticket_id}", headers=api_headers, timeout=10)
            require_status(absent, 404, "Проверка удаления собственной заявки")
            log.info("Собственная заявка удалена", extra={"fields": {"ticket_id": ticket_id}})
        except Exception as error:
            errors.append(f"заявка: {type(error).__name__}: {error}")
            log.error(
                "Ошибка очистки собственной заявки",
                extra={"fields": {"ticket_id": ticket_id, "error_type": type(error).__name__}},
            )
    for label, token in (("api", api_token), ("browser", browser_token)):
        if not token:
            continue
        try:
            revoke_session(session, base_url, token, label)
        except Exception as error:
            errors.append(f"сессия {label}: {type(error).__name__}: {error}")
            log.error(
                "Ошибка отзыва сессии",
                extra={"fields": {"session_kind": label, "error_type": type(error).__name__}},
            )
    return errors


def run(args):
    """Выполнить UI-сценарий и всегда очистить только созданные им данные и сессии."""
    base_url = args.base_url.rstrip("/")
    title = f"Ожидание Playwright {uuid.uuid4()}"
    report = {
        "ticket_id": None,
        "immediate": None,
        "final": None,
        "wait_elapsed_ms": None,
        "passed": False,
    }
    session = requests.Session()
    session.trust_env = False
    api_token = None
    browser_token = None
    ticket_id = None
    browser = None
    context = None
    page = None
    playwright = None
    failure = None
    log.info(
        "Запуск проверки ожидания",
        extra={"fields": {"latency_ms": args.latency_ms, "timeout_ms": args.timeout_ms}},
    )
    try:
        api_token, ticket_id = api_setup(session, base_url, title)
        report["ticket_id"] = ticket_id
        log.info("Тестовая заявка создана", extra={"fields": {"ticket_id": ticket_id}})

        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=not args.headed,
            args=["--no-proxy-server"],
        )
        context = browser.new_context()
        page = context.new_page()
        page.goto(base_url)
        page.get_by_label("Email", exact=True).fill(EMAIL)
        page.get_by_label("Пароль", exact=True).fill(PASSWORD)
        page.get_by_role("button", name="Войти", exact=True).click()
        expect(page.get_by_role("button", name="Создать заявку", exact=True)).to_be_enabled()
        browser_token = page.evaluate("sessionStorage.getItem('lab-token')")

        row = page.get_by_test_id(f"ticket-{ticket_id}")
        expect(row).to_be_visible()
        row.get_by_role("button", name=title, exact=True).click()
        page.get_by_label("Приоритет заявки", exact=True).select_option("high")
        save = page.get_by_role("button", name="Сохранить изменения", exact=True)
        expect(save).to_be_enabled()

        cdp = context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send(
            "Network.emulateNetworkConditions",
            {
                "offline": False,
                "latency": args.latency_ms,
                "downloadThroughput": -1,
                "uploadThroughput": -1,
            },
        )
        priority = row.get_by_test_id("ticket-priority")
        log.info(
            "Ожидание изменения текста начато",
            extra={"fields": {"condition": "ticket-priority == Высокий", "timeout_ms": args.timeout_ms}},
        )
        save.click()
        report["immediate"] = priority.inner_text()
        started = time.perf_counter()
        try:
            expect(priority).to_have_text("Высокий", timeout=args.timeout_ms)
        finally:
            report["wait_elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
            report["final"] = priority.inner_text()
        expect(page.get_by_role("status")).to_have_text("Изменения сохранены", timeout=args.timeout_ms)
        report["passed"] = True
        log.info(
            "Условие ожидания выполнено",
            extra={"fields": {"condition": "ticket-priority == Высокий", "elapsed_ms": report["wait_elapsed_ms"]}},
        )
    except Exception as error:
        failure = error
        log.error(
            "Проверка ожидания завершилась ошибкой",
            extra={
                "fields": {
                    "condition": "ticket-priority == Высокий",
                    "timeout_ms": args.timeout_ms,
                    "error_type": type(error).__name__,
                }
            },
        )
    finally:
        if api_token is None:
            authorization = session.headers.get("Authorization", "")
            if authorization.startswith("Bearer "):
                api_token = authorization.removeprefix("Bearer ")
        if page is not None and not page.is_closed() and browser_token is None:
            try:
                browser_token = page.evaluate("sessionStorage.getItem('lab-token')")
            except Exception:
                log.error("Не удалось прочитать токен браузерной сессии")
        cleanup_errors = cleanup(session, base_url, api_token, browser_token, ticket_id)
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()
        session.close()
        if cleanup_errors:
            report["cleanup_errors"] = cleanup_errors
            report["passed"] = False
        else:
            report["cleanup"] = "created_resources_removed"

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failure is not None:
        print(f"Ошибка ожидания: {type(failure).__name__}", file=sys.stderr)
    return 0 if report["passed"] and not failure else 1


def main():
    """Разобрать параметры локального учебного запуска."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--latency-ms", type=int, default=900)
    parser.add_argument("--timeout-ms", type=int, default=7000)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    if args.latency_ms < 0:
        parser.error("--latency-ms не может быть отрицательным")
    if args.timeout_ms <= 0:
        parser.error("--timeout-ms должен быть положительным")
    if not CHROME.is_file():
        parser.error(f"Chrome не найден: {CHROME}")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
