"""Статическая проверка OpenAPI/Pydantic: null, отсутствие поля и пустой PATCH не смешиваются."""

import pytest
from pydantic import ValidationError

from backend.schemas import TicketPatch


def test_patch_contract_does_not_allow_null_or_empty_object():
    """Проверить машиночитаемую схему, а не только фактический ответ API."""
    schema = TicketPatch.model_json_schema()
    assert schema["minProperties"] == 1
    for field in ["title", "priority"]:
        assert schema["properties"][field]["type"] == "string"
        assert "default" not in schema["properties"][field]


@pytest.mark.parametrize("field", ["title", "priority"])
def test_patch_rejects_explicit_null_but_accepts_missing_field(field):
    """Сравнить два класса входа: не переданное поле и явно переданный null."""
    assert TicketPatch().model_dump(exclude_unset=True) == {}
    with pytest.raises(ValidationError):
        TicketPatch.model_validate({field: None})
