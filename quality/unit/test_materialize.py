"""Проверки архитектурных образов, создаваемых генератором вариантов."""

from pathlib import Path

import yaml

from scripts.materialize import ROOT, configure


def generated_compose(tmp_path: Path, architecture: str) -> dict:
    """Создать минимальное дерево назначения и прочитать сгенерированный Compose."""
    (tmp_path / "deploy").mkdir()
    configure(tmp_path, architecture, "fixed")
    return yaml.safe_load((tmp_path / "compose.yaml").read_text(encoding="utf-8"))


def test_client_server_uses_backend_only_application_image(tmp_path):
    """Клиент-серверный вариант должен собирать API и интерфейс разными образами."""
    services = generated_compose(tmp_path, "client-server")["services"]

    assert services["app"]["build"] == {
        "context": ".",
        "dockerfile": "deploy/Dockerfile.backend",
        "target": "application",
    }
    assert services["app"]["image"] == "${LAB_PROJECT:-mini-tickets}-application:${LAB_IMAGE_TAG:-local}"
    assert services["web"]["image"] == "${LAB_PROJECT:-mini-tickets}-web:${LAB_IMAGE_TAG:-local}"


def test_microservices_use_distinct_targets_and_images(tmp_path):
    """Сервисы пользователей и заявок должны иметь собственные targets и имена образов."""
    services = generated_compose(tmp_path, "microservices")["services"]

    assert "app" not in services
    assert services["identity"]["build"]["target"] == "identity"
    assert services["tickets"]["build"]["target"] == "tickets"
    assert services["identity"]["image"] == "${LAB_PROJECT:-mini-tickets}-identity:${LAB_IMAGE_TAG:-local}"
    assert services["tickets"]["image"] == "${LAB_PROJECT:-mini-tickets}-tickets:${LAB_IMAGE_TAG:-local}"
    assert services["identity"]["image"] != services["tickets"]["image"]


def test_monolith_keeps_combined_root_dockerfile(tmp_path):
    """Монолит должен продолжать собираться корневым многостадийным Dockerfile."""
    app = generated_compose(tmp_path, "monolith")["services"]["app"]

    assert app["build"]["context"] == "."
    assert "dockerfile" not in app["build"]
    assert "target" not in app["build"]


def test_backend_dockerfile_has_no_frontend_build_context():
    """Backend-only образ не должен зависеть от исходников интерфейса или Node.js."""
    dockerfile = (ROOT / "deploy/Dockerfile.backend").read_text(encoding="utf-8").lower()

    assert "frontend" not in dockerfile
    assert "node:" not in dockerfile
    assert "npm " not in dockerfile
    assert "copy migrations/ migrations/" in dockerfile
    assert "user lab" in dockerfile
    assert all(f"from runtime as {target}" in dockerfile for target in ("application", "identity", "tickets"))
