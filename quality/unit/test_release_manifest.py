"""Проверки схемы и локальной доступности манифеста выпуска."""

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("validate_release", ROOT / "scripts/validate_release.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def write_manifest(root: Path, version: str, content: object) -> None:
    """Записать минимальный манифест в изолированную временную директорию."""
    directory = root / "releases"
    directory.mkdir()
    (directory / f"{version}.json").write_text(json.dumps(content), encoding="utf-8")


def test_current_manifest_references_local_variants():
    """Действующий выпуск проверяется по локальной истории Git без сетевого доступа."""
    manifest = validator.validate_release(ROOT, "1.0.0")
    assert tuple(manifest) == validator.BRANCHES


@pytest.mark.parametrize("version", ["v1.0.0", "1.0", "1.0.0-rc.1", "01.0.0"])
def test_invalid_version_is_rejected(version):
    """Тег выпуска не должен допускать неоднозначный формат имени."""
    with pytest.raises(validator.ReleaseValidationError, match="MAJOR.MINOR.PATCH"):
        validator.validate_version(version)


def test_manifest_requires_exact_set_of_branches(tmp_path):
    """Манифест без варианта или с посторонней веткой не проходит публикацию."""
    invalid = {branch: "a" * 40 for branch in validator.BRANCHES[:-1]}
    invalid["other/fixed"] = "b" * 40
    write_manifest(tmp_path, "2.0.0", invalid)
    with pytest.raises(validator.ReleaseValidationError, match="только шесть веток"):
        validator.load_manifest(tmp_path, "2.0.0")


def test_manifest_requires_full_lowercase_sha(tmp_path):
    """Сокращённый или заглавный SHA не может зафиксировать воспроизводимый выпуск."""
    invalid = {branch: "a" * 40 for branch in validator.BRANCHES}
    invalid["monolith/fixed"] = "A" * 40
    write_manifest(tmp_path, "2.0.0", invalid)
    with pytest.raises(validator.ReleaseValidationError, match="40 строчных"):
        validator.load_manifest(tmp_path, "2.0.0")


def test_commit_variant_must_match_manifest_branch():
    """Даже существующий коммит нельзя отнести к варианту с другой архитектурой или состоянием."""
    def fake_git(_root, arguments):
        """Вернуть вариант, отличный от ключа манифеста, без запуска внешнего Git."""
        if arguments[0] == "show":
            return '{"architecture": "monolith", "state": "buggy"}'
        return ""

    with pytest.raises(validator.ReleaseValidationError, match="не соответствует ветке"):
        validator.validate_commit(ROOT, "monolith/fixed", "a" * 40, fake_git)
