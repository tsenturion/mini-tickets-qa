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
    "15-итоговый-регрессионный-прогон.md",
]
PRODUCT_BRANCHES = [
    "monolith/fixed",
    "monolith/buggy",
    "client-server/fixed",
    "client-server/buggy",
    "microservices/fixed",
    "microservices/buggy",
]


def test_catalog_reserves_fifteen_assignments_and_links_published_works():
    """Индекс содержит ссылки на все пятнадцать опубликованных работ."""
    text = (CATALOG / "README.md").read_text(encoding="utf-8")
    items = re.findall(r"(?m)^(\d+)\. (.+)$", text)
    assert [int(number) for number, _ in items] == list(range(1, 16))
    linked = re.findall(r"(?m)^\d+\. \[[^]]+\]\(([^)]+)\)$", text)
    assert linked == PUBLISHED_ASSIGNMENTS
    assert all((CATALOG / target).is_file() for target in linked)
    assert not any(label.endswith("— запланировано.") for _, label in items)


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


def test_program_coverage_map_names_all_modules_and_deep_practices():
    """Карта покрытия связывает программу с работами и углублёнными модулями."""
    coverage = (CATALOG / "ПОКРЫТИЕ-ПРОГРАММЫ.md").read_text(encoding="utf-8")
    for number in range(1, 9):
        assert f"{number}. " in coverage
    assert "№ 8, № 9, № 12" in coverage
    assert "№ 10, № 11" in coverage
    assert "№ 13, № 14" in coverage


def test_each_product_branch_is_used_before_the_final_practice():
    """Каждая продуктовая ветка прямо используется в работах с третьей по четырнадцатую."""
    texts = [
        (CATALOG / name).read_text(encoding="utf-8")
        for name in PUBLISHED_ASSIGNMENTS[2:14]
    ]
    combined = "\n".join(texts)
    for branch in PRODUCT_BRANCHES:
        assert branch in combined


def test_result_workflow_covers_pull_merge_requests_and_ci():
    """Общий цикл результата включает обе площадки, PR/MR и проверку CI."""
    catalog = (CATALOG / "README.md").read_text(encoding="utf-8")
    for phrase in ("GitHub", "GitLab", "PR/MR", "GitHub Actions", "GitLab CI"):
        assert phrase in catalog
    for name in PUBLISHED_ASSIGNMENTS[1:]:
        text = (CATALOG / name).read_text(encoding="utf-8")
        for phrase in ("git push", "PR", "MR"):
            assert phrase in text
    for name in PUBLISHED_ASSIGNMENTS[2:14]:
        text = (CATALOG / name).read_text(encoding="utf-8")
        for phrase in ("GitHub Actions", "GitLab CI"):
            assert phrase in text


def test_assignments_do_not_describe_mandatory_submission():
    """Практики не вводят обязательную сдачу или обязательные элементы."""
    forbidden = (
        "обязательная сдача",
        "обязательные элементы",
        "обязательный элемент",
        "сдать работу",
        "сдайте ссылку",
        "для сдачи",
    )
    student_facing = [CATALOG / name for name in PUBLISHED_ASSIGNMENTS]
    student_facing.extend(
        [
            CATALOG / "README.md",
            ROOT / "docs/CI.md",
            ROOT / "student-template/README.md",
        ]
    )
    for path in student_facing:
        text = path.read_text(encoding="utf-8").casefold()
        for phrase in forbidden:
            assert phrase not in text
