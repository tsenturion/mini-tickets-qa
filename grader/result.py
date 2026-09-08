"""Правила оценивания, независимые от конкретной CI и Docker."""
from dataclasses import asdict, dataclass

REQUIREMENTS = {"D01": "TICKET-01", "D02": "TICKET-02", "D03": "AUTH-03", "D04": "TICKET-04",
                "D05": "TICKET-05", "D06": "COMMENT-01", "D07": "UI-02", "D08": "UI-03"}


@dataclass
class Verdict:
    """Итог оценки: найденные/пропущенные дефекты, процент и причина без привязки к CI-площадке."""
    status: str
    detected: list[str]
    missed: list[str]
    score: float
    reason: str

    def to_dict(self):
        """Преобразовать результат в JSON-совместимую структуру для отчёта и проверок CI."""
        return asdict(self)


def assess(baselines, mutants, assigned, threshold=0.75):
    """Засчитать только осмысленное падение на подтверждённом дефекте после полностью успешных эталонов."""
    if not assigned or not set(assigned) <= REQUIREMENTS.keys():
        return Verdict("configuration_error", [], [], 0, "Неизвестный или пустой набор дефектов")
    if not baselines or any(run.get("infrastructure_error") for run in baselines.values()):
        return Verdict("infrastructure_error", [], list(assigned), 0, "Исправленный стенд не проверен")
    cases = next(iter(baselines.values())).get("cases", {})
    if not cases:
        return Verdict("invalid_submission", [], list(assigned), 0, "Тесты не обнаружены")
    for run in baselines.values():
        if run.get("exit_code") != 0 or set(run.get("cases", {})) != set(cases):
            return Verdict("invalid_submission", [], list(assigned), 0, "Исправленные прогоны не совпадают или завершились ошибкой")
        if any(case["outcome"] != "passed" for case in run["cases"].values()):
            return Verdict("invalid_submission", [], list(assigned), 0, "На исправленном стенде есть падения, ошибки или пропуски")
    if not {"api", "ui"} <= {case.get("kind") for case in cases.values()}:
        return Verdict("invalid_submission", [], list(assigned), 0, "Нужны API- и UI-тесты")
    detected = []
    # Один и тот же набор тестов должен проходить исправленный продукт и падать
    # проверкой требования на одиночном мутанте. Сам по себе красный pytest ничего не доказывает.
    for defect in assigned:
        runs = mutants.get(defect, [])
        if not runs or any(run.get("infrastructure_error") or not run.get("control_confirmed") for run in runs):
            return Verdict("infrastructure_error", detected, [d for d in assigned if d not in detected], 0, f"Не подтверждён вариант {defect}")
        found_everywhere = True
        for run in runs:
            current = run.get("cases", {})
            if set(current) != set(cases) or run.get("exit_code") not in {0, 1}:
                return Verdict("invalid_submission", detected, list(assigned), 0, "Набор тестов меняется или не запускается на дефектном варианте")
            found = any(case["outcome"] == "failed" and case.get("assertion") and REQUIREMENTS[defect] in case.get("requirements", [])
                        and (defect not in {"D07", "D08"} or case.get("kind") == "ui") for case in current.values())
            found_everywhere &= found
        if found_everywhere:
            detected.append(defect)
    score = len(detected) / len(assigned)
    return Verdict("passed" if score >= threshold else "failed", detected, [d for d in assigned if d not in detected],
                   round(score * 100, 2), "Исправленные версии пройдены; обнаружение считается по назначенным требованиям")
