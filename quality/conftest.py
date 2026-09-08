"""Фикстуры преподавателя: уникальные данные, очистка и доказательства браузерного падения."""

import os
from pathlib import Path

import pytest

from quality.support import Client


@pytest.fixture
def url():
    """Получить единственную внешнюю точку входа: тестам не нужны имена внутренних сервисов."""
    return os.getenv("BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture
def api(url):
    """Создать нового пользователя на тест и удалить его новые заявки в teardown; полный сброс делает временная БД."""
    client = Client(url).register()
    yield client
    # Новые заявки удаляем через API. Остальные данные удаляет запускатель среды.
    response = client.request("GET", "/tickets")
    if response.status_code == 200:
        for ticket in response.json():
            if ticket["status"] == "new":
                client.request("DELETE", f"/tickets/{ticket['id']}")
    client.session.close()


@pytest.fixture
def operator(url):
    """Выдать отдельную HTTP-сессию подготовленного оператора, не передавая его токен другим тестам."""
    client = Client(url).login("operator@example.test")
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Разрешить явно выбранный браузер при локальной диагностике, сохранив настройки Playwright."""
    executable = os.getenv("PLAYWRIGHT_EXECUTABLE_PATH")
    if executable:
        return {**browser_type_launch_args, "executable_path": executable}
    return browser_type_launch_args


@pytest.fixture
def logged_page(page, api, url, tmp_path):
    """Войти через UI как уникальный пользователь и сохранить Console/pageerror для разбора падений."""
    console = []
    page.on("console", lambda message: console.append(f"{message.type}: {message.text}"))
    page.on("pageerror", lambda error: console.append(str(error)))
    page.goto(url)
    page.get_by_label("Email", exact=True).fill(api.email)
    page.get_by_label("Пароль", exact=True).fill("LabPassword1!")
    page.get_by_role("button", name="Войти", exact=True).click()
    page.get_by_role("heading", name="Заявки").wait_for()
    yield page
    output = Path(os.getenv("ARTIFACT_DIR", "artifacts/browser"))
    output.mkdir(parents=True, exist_ok=True)
    (output / (tmp_path.name + ".console.log")).write_text("\n".join(console), encoding="utf-8")
