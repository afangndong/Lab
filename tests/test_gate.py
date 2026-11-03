from gate import check_change
from tickets import FakeClient


def test_blocks_wrong_state(data):
    c = FakeClient({"CHG1": {"short_description": "x", "state": "new"}})
    assert check_change("CHG1", c, data) == 1
    assert "nicht freigegeben" in c.notes["CHG1"][-1]


def test_ok(data):
    c = FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})
    assert check_change("CHG1", c, data) == 0
    assert c.notes["CHG1"][-1].startswith("Pipeline")


def test_unknown_ticket(data):
    assert check_change("CHG9", FakeClient({}), data) == 1


def test_invalid_data_blocks(data):
    data["sites"][0]["lan"] = "kein-netz"
    c = FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})
    assert check_change("CHG1", c, data) == 1
    assert "Validierung fehlgeschlagen" in c.notes["CHG1"][-1]