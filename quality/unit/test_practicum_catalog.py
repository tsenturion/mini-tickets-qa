"""Проверяет структуру каталога практических работ без привязки к составу группы."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/Практические-работы"
PUBLISHED_ASSIGNMENTS = [
    "01-знакомство-с-архитектурами.md",
    "02-ci-cd-и-репозиторий-работ.md",
    "03-проектирование-набора-тестов.md",
    "04-ревью-требований-и-тестовая-документация.md",
    "05-исследовательская-сессия-и-дефекты.md",
    "06-безопасность-удобство-и-совместимость.md",
    "07-нагрузочное-и-стресс-тестирование.md",
    "08-ручное-тестирование-rest-api.md",
    "09-api-тесты-на-python-и-диагностика-ошибок.md",
    "10-sql-и-проверка-структуры-данных.md",
    "11-api-postgresql-и-управление-тестовыми-данными.md",
    "12-api-и-отладка.md",
    "13-автоматизация-ui-на-playwright.md",
    "14-автотесты-в-ci.md",
]


def test_catalog_reserves_fifteen_assignments_and_links_published_works():
    """Индекс содержит 15 позиций и ссылки на четырнадцать опубликованных работ."""
    text = (CATALOG / "README.md").read_text(encoding="utf-8")
    items = re.findall(r"(?m)^(\d+)\. (.+)$", text)
    assert [int(number) for number, _ in items] == list(range(1, 16))
    linked = re.findall(r"(?m)^\d+\. \[[^]]+\]\(([^)]+)\)$", text)
    assert linked == PUBLISHED_ASSIGNMENTS
    assert all((CATALOG / target).is_file() for target in linked)
    assert all(label.endswith("— запланировано.") for _, label in items[14:])


def test_fourth_assignment_has_review_materials():
    """Четвёртая работа содержит четыре отдельных исходника для статического ревью."""
    materials = CATALOG / "materials" / "04-requirements-review"
    assert sorted(path.name for path in materials.iterdir() if path.is_file()) == [
        "README.md",
        "openapi-fragment.yaml",
        "srs-fragment.md",
        "use-case.md",
        "user-story.md",
    ]
    published = sorted(path.name for path in CATALOG.glob("[0-9][0-9]-*.md"))
    assert published == PUBLISHED_ASSIGNMENTS
    assert not (ROOT / "docs/ПРАКТИКУМ.md").exists()
