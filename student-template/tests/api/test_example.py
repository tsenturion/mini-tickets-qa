import pytest
import requests


@pytest.mark.api
@pytest.mark.requirement("AUTH-02")
def test_current_user_requires_token(url):
    response = requests.get(url + "/api/auth/me", timeout=5)
    assert response.status_code == 401

