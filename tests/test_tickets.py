import pytest
from tickets import FakeClient, ServiceNowClient, client_from_env


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


def test_client_from_env(monkeypatch):
    monkeypatch.delenv("TICKET_SYSTEM", raising=False)
    monkeypatch.setenv("SERVICENOW_URL", "http://example:1234")
    c = client_from_env()
    assert isinstance(c, ServiceNowClient)
    assert c.base_url == "http://example:1234"