"""Маленький HTTP-клиент контрольных тестов с уникальными данными и явными тайм-аутами."""

import uuid

import requests


class Client:
    """Обёртка Requests без доступа к реализации продукта или его БД."""
    def __init__(self, base_url):
        """Создать независимую сессию без общих cookies/заголовков между пользователями."""
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def request(self, method, path, **kwargs):
        """Отправить запрос к внешнему /api и ограничить ожидание ответа десятью секундами."""
        return self.session.request(method, self.base_url + "/api" + path, timeout=10, **kwargs)

    def login(self, email, password="LabPassword1!"):
        """Войти заданным пользователем и сохранить Bearer только в собственной тестовой сессии."""
        response = self.request("POST", "/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        self.session.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        return self

    def register(self):
        """Создать уникальный email, запомнить публичного пользователя и выполнить вход."""
        self.email = f"test-{uuid.uuid4().hex}@example.test"
        response = self.request("POST", "/auth/register", json={"email": self.email, "password": "LabPassword1!"})
        assert response.status_code == 201, response.text
        self.user = response.json()
        return self.login(self.email)

    def create(self, title=None, priority="normal"):
        """Подготовить заявку для следующего действия теста и проверить успешность предусловия."""
        response = self.request("POST", "/tickets", json={"title": title or f"Заявка {uuid.uuid4().hex}", "priority": priority})
        assert response.status_code == 201, response.text
        return response.json()
