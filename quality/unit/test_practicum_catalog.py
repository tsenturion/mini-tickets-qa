"""Проверяет структуру каталога практических работ без привязки к составу группы."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/Практические-работы"


def test_catalog_reserves_fifteen_assignments_and_links_published_works():
    """Индекс содержит 15 позиций и ссылки на четыре опубликованные работы."""
    text = (CATALOG / "README.md").read_text(encoding="utf-8")
    items = re.findall(r"(?m)^(\d+)\. (.+)$", text)
    assert [int(number) for number, _ in items] == list(range(1, 16))
    linked = re.findall(r"(?m)^\d+\. \[[^]]+\]\(([^)]+)\)$", text)
    assert linked == [
        "01-знакомство-с-архитектурами.md",
        "02-ci-cd-и-репозиторий-работ.md",
        "03-проектирование-набора-тестов.md",
        "04-ревью-требований-и-тестовая-документация.md",
    ]
    assert all((CATALOG / target).is_file() for target in linked)
    assert all(label.endswith("— запланировано.") for _, label in items[4:])


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
    assert published == linked
    assert not (ROOT / "docs/ПРАКТИКУМ.md").exists()
