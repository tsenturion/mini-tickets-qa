"""Наблюдатель фиксирует фазу падения, чтобы не засчитывать ошибки подготовки."""
import json
import os
from pathlib import Path

import pytest

cases = {}


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
    """Зафиксировать выбранные после -k тесты и требования; обратный порядок выявляет зависимости между тестами."""
    if os.getenv("REVERSE_TEST_ORDER") == "1":
        items.reverse()
    for item in items:
        cases[item.nodeid] = {"outcome": "not_run", "assertion": False,
            "requirements": [mark.args[0] for mark in item.iter_markers("requirement") if mark.args],
            "kind": "ui" if item.get_closest_marker("ui") else "api" if item.get_closest_marker("api") else "other"}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Различить AssertionError в call и сбой setup/teardown: ошибка подготовки не считается найденным дефектом."""
    # Ждём стандартный отчёт pytest: до yield исход фазы ещё неизвестен.
    # Ошибка teardown должна отменять успешный call, а не засчитываться как найденный дефект.
    report = (yield).get_result()
    case = cases[item.nodeid]
    if report.when == "call":
        case.update(outcome=report.outcome, assertion=bool(call.excinfo and call.excinfo.errisinstance(AssertionError)))
    elif report.failed:
        case.update(outcome="error", assertion=False)
    elif report.skipped:
        case.update(outcome="skipped", assertion=False)


def pytest_sessionfinish(session, exitstatus):
    """Сохранить полный наблюдаемый набор, включая not_run, для сравнения эталона и дефектной версии."""
    destination = Path(os.environ["OBSERVER_REPORT"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"exit_code": int(exitstatus), "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
