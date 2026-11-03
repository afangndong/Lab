import copy

import pytest
from fastapi.testclient import TestClient

from mocks import mock_servicenow as m
from tickets import ServiceNowClient


@pytest.fixture
def client():
    m.CHANGES.clear()
    m.CHANGES.update(copy.deepcopy(m.INITIAL))
    # Der TestClient ersetzt die echte Verbindung, ohne Server zu starten
    return ServiceNowClient("", session=TestClient(m.app))


def test_get_change(client):
    ch = client.get_change("CHG0030412")
    assert ch.number == "CHG0030412"
    assert ch.state == "scheduled"


def test_add_note(client):
    client.add_note("CHG0030412", "Pipeline gestartet")
    assert m.CHANGES["abc1"]["work_notes"] == ["Pipeline gestartet"]


def test_set_state(client):
    client.set_state("CHG0030412", "closed")
    assert client.get_change("CHG0030412").state == "closed"


def test_unknown_change_raises(client):
    with pytest.raises(KeyError):
        client.get_change("CHG9999999")