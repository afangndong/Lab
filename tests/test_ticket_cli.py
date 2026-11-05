import pytest

from ticket_cli import main
from tickets import FakeClient


def _client():
    return FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})


def test_note():
    c = _client()
    assert main(["note", "CHG1", "ausgerollt"], client=c) == 0
    assert c.notes["CHG1"] == ["ausgerollt"]


def test_state():
    c = _client()
    assert main(["state", "CHG1", "closed"], client=c) == 0
    assert c.get_change("CHG1").state == "closed"


def test_unknown_command():
    with pytest.raises(SystemExit):
        main(["gibtsnicht"], client=_client())