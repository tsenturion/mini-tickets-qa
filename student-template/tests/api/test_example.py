"""Нейтральный стартовый API-тест: показывает структуру, но не обнаруживает назначенные дефекты."""

import pytest
import requests


@pytest.mark.api
@pytest.mark.requirement("AUTH-02")
def test_current_user_requires_token(url):
    """Проверить AUTH-02: без Bearer ответ 401, а не данные пользователя."""
    response = requests.get(url + "/api/auth/me", timeout=5)
    assert response.status_code == 401
