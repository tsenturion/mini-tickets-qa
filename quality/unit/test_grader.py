from copy import deepcopy

import pytest

from grader.result import assess


def run(outcome="passed", requirement="TICKET-01"):
    return {"exit_code": 0 if outcome == "passed" else 1, "control_confirmed": True, "cases": {
        "api": {"outcome": outcome, "kind": "api", "requirements": [requirement], "assertion": outcome == "failed"},
        "ui": {"outcome": "passed", "kind": "ui", "requirements": ["UI-02"], "assertion": False}}}


def test_good_submission_and_always_failing():
    assert assess({"fixed": run()}, {"D01": [run("failed")]}, ["D01"]).status == "passed"
    assert assess({"fixed": run("failed")}, {"D01": [run("failed")]}, ["D01"]).status == "invalid_submission"


@pytest.mark.parametrize("outcome", ["skipped", "error", "not_run"])
def test_baseline_must_pass(outcome):
    baseline = run(outcome)
    baseline["exit_code"] = 0
    assert assess({"fixed": baseline}, {}, ["D01"]).status == "invalid_submission"


def test_empty_and_infrastructure_are_not_kills():
    assert assess({"fixed": {"cases": {}, "exit_code": 0}}, {}, ["D01"]).status == "invalid_submission"
    assert assess({"fixed": {"infrastructure_error": True}}, {}, ["D01"]).status == "infrastructure_error"
    assert assess({"fixed": run()}, {"D01": [{"infrastructure_error": True}]}, ["D01"]).status == "infrastructure_error"


def test_setup_error_and_irrelevant_assertion_do_not_count():
    assert assess({"fixed": run()}, {"D01": [run("error")]}, ["D01"]).score == 0
    assert assess({"fixed": run()}, {"D01": [run("failed", "OTHER")]}, ["D01"]).score == 0


def test_partial_score_and_architecture_portability():
    result = assess({"fixed": run()}, {"D01": [run("failed")], "D02": [run()]}, ["D01", "D02"])
    assert result.score == 50 and result.status == "failed"
    assert assess({"fixed": run()}, {"D01": [run("failed"), run()]}, ["D01"]).score == 0


def test_ui_defect_needs_ui_assertion():
    assert assess({"fixed": run()}, {"D07": [run("failed", "UI-02")]}, ["D07"]).score == 0


def test_changed_collection_is_invalid():
    mutant = run("failed")
    mutant["cases"]["extra"] = deepcopy(mutant["cases"]["api"])
    assert assess({"fixed": run()}, {"D01": [mutant]}, ["D01"]).status == "invalid_submission"
