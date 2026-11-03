import pytest
from tickets import FakeClient


def test_get_change():
    c = FakeClient({"CHG1": {"short_description": "Filiale", "state": "scheduled"}})
    ch = c.get_change("CHG1")
    assert ch.number == "CHG1" and ch.state == "scheduled"


def test_add_note_is_stored():
    c = FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})
    c.add_note("CHG1", "Pipeline gestartet")
    assert c.notes["CHG1"] == ["Pipeline gestartet"]


def test_set_state():
    c = FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})
    c.set_state("CHG1", "closed")
    assert c.get_change("CHG1").state == "closed"


def test_unknown_change_raises():
    with pytest.raises(KeyError):
        FakeClient({}).get_change("CHG9")