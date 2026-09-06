import pytest
from pydantic import ValidationError

from backend import policy
from backend.schemas import CommentInput, Credentials, TicketCreate, TicketPatch


@pytest.mark.parametrize("length", [0, 1, 2, 81, 100])
def test_title_invalid(length):
    with pytest.raises(ValueError):
        policy.title_value("a" * length)


@pytest.mark.parametrize("length", [3, 4, 79, 80])
def test_title_valid(length):
    assert policy.title_value(" " + "a" * length + " ") == "a" * length


@pytest.mark.parametrize("old", sorted(policy.STATUSES))
@pytest.mark.parametrize("new", sorted(policy.STATUSES))
def test_transitions(old, new):
    expected = old == new or (old, new) in {("new", "active"), ("active", "closed"), ("closed", "active")}
    assert policy.transition_allowed(old, new) == expected


@pytest.mark.parametrize("role,actor,owner,expected", [("user", 1, 1, True), ("user", 1, 2, False), ("operator", 1, 2, True)])
def test_permissions(role, actor, owner, expected):
    assert policy.visible(role, actor, owner) == expected


def test_input_contract():
    assert Credentials(email=" A@EXAMPLE.TEST ", password="12345678").email == "a@example.test"
    for payload in [{"title": "ok!", "priority": "urgent"}, {"title": "ok!", "author_id": "spoof"}]:
        with pytest.raises(ValidationError):
            TicketCreate(**payload)
    with pytest.raises(ValidationError):
        TicketPatch(title=None)
    with pytest.raises(ValidationError):
        CommentInput(text="  ")
    assert CommentInput(text="  текст  ").text == "текст"

