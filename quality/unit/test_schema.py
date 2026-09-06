import pytest
from pydantic import ValidationError

from backend.schemas import TicketPatch


def test_patch_contract_does_not_allow_null_or_empty_object():
    schema = TicketPatch.model_json_schema()
    assert schema["minProperties"] == 1
    for field in ["title", "priority"]:
        assert schema["properties"][field]["type"] == "string"
        assert "default" not in schema["properties"][field]


@pytest.mark.parametrize("field", ["title", "priority"])
def test_patch_rejects_explicit_null_but_accepts_missing_field(field):
    assert TicketPatch().model_dump(exclude_unset=True) == {}
    with pytest.raises(ValidationError):
        TicketPatch.model_validate({field: None})
