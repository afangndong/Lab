import copy

import pytest
from fastapi.testclient import TestClient

from mocks import mock_servicenow as m

URL = "/api/now/table/change_request"


@pytest.fixture
def client():
    m.CHANGES.clear()
    m.CHANGES.update(copy.deepcopy(m.INITIAL))
    return TestClient(m.app)


def test_get_by_number(client):
    r = client.get(URL, params={"sysparm_query": "number=CHG0030412"})
    assert r.status_code == 200
    result = r.json()["result"]
    assert len(result) == 1
    assert result[0]["number"] == "CHG0030412"
    assert result[0]["state"] == "scheduled"


def test_get_unknown_number_gives_empty_list(client):
    r = client.get(URL, params={"sysparm_query": "number=CHG9999999"})
    assert r.json() == {"result": []}


def test_patch_state(client):
    r = client.patch(f"{URL}/abc1", json={"state": "closed"})
    assert r.status_code == 200
    r2 = client.get(URL, params={"sysparm_query": "number=CHG0030412"})
    assert r2.json()["result"][0]["state"] == "closed"


def test_patch_work_note(client):
    client.patch(f"{URL}/abc1", json={"work_notes": "Pipeline gestartet"})
    r = client.get(URL, params={"sysparm_query": "number=CHG0030412"})
    assert r.json()["result"][0]["work_notes"] == ["Pipeline gestartet"]


def test_patch_unknown_sys_id(client):
    r = client.patch(f"{URL}/gibtsnicht", json={"state": "closed"})
    assert r.status_code == 404