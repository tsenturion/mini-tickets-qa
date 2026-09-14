"""Проверяет структуру каталога практических работ без привязки к составу группы."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/Практические-работы"


def test_catalog_reserves_fifteen_assignments_and_links_existing_nine():
    """Индекс содержит 15 позиций, а ссылки первых девяти ведут к отдельным файлам."""
    text = (CATALOG / "README.md").read_text(encoding="utf-8")
    items = re.findall(r"(?m)^(\d+)\. (.+)$", text)
    assert [int(number) for number, _ in items] == list(range(1, 16))
    linked = re.findall(r"(?m)^[1-9]\. \[[^]]+\]\(([^)]+)\)$", text)
    assert len(linked) == 9
    assert all((CATALOG / target).is_file() for target in linked)
    assert all(label == "Будет добавлено." for _, label in items[9:])
    assert not (ROOT / "docs/ПРАКТИКУМ.md").exists()
