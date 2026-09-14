"""Проверки локальной сборки файлов выпуска без сетевого доступа."""

import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("package_release", ROOT / "scripts/package_release.py")
packager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packager)


def test_current_release_creates_manifest_archives_and_checksums(tmp_path):
    """Действующий манифест собирается в шесть архивов с проверяемыми суммами."""
    output = tmp_path / "release"
    files = packager.package_release(ROOT, "1.0.0", output)

    manifest = json.loads((output / "1.0.0.json").read_text(encoding="utf-8"))
    archives = [output / packager.archive_name("1.0.0", branch) for branch in packager.BRANCHES]
    assert len(files) == 8
    assert all(archive.is_file() for archive in archives)
    for branch, archive in zip(packager.BRANCHES, archives, strict=True):
        with zipfile.ZipFile(archive) as package:
            prefix = f"mini-tickets-qa-1.0.0-{branch.replace('/', '-')}/"
            assert prefix + "variant.json" in package.namelist()
            variant = json.loads(package.read(prefix + "variant.json"))
        architecture, state = branch.split("/", maxsplit=1)
        assert variant["architecture"] == architecture
        assert variant["state"] == state
        assert manifest[branch]

    checksum_lines = (output / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    assert len(checksum_lines) == 7
    for line in checksum_lines:
        digest, filename = line.split("  ", maxsplit=1)
        assert digest == hashlib.sha256((output / filename).read_bytes()).hexdigest()


def test_output_must_be_new_or_empty(tmp_path):
    """Сборщик не перезаписывает уже подготовленный каталог результата."""
    output = tmp_path / "occupied"
    output.mkdir()
    (output / "existing.txt").write_text("данные", encoding="utf-8")
    with pytest.raises(packager.ReleasePackagingError, match="пустым"):
        packager.prepare_output(ROOT, output)


def test_output_must_not_be_project_root():
    """Сборщик защищает корень проекта от записи служебных файлов выпуска."""
    with pytest.raises(packager.ReleasePackagingError, match="корнем"):
        packager.prepare_output(ROOT, ROOT)
