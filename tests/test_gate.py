from gate import check_change, main
from tickets import FakeClient
import generate


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



def test_main_needs_one_argument():
    assert main([]) == 2


def _write_generated(data, root):
    for p, t in generate.render_all(data, root=root).items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")


def test_ok(data, tmp_path):
    _write_generated(data, tmp_path)
    c = FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})
    assert check_change("CHG1", c, data, root=tmp_path) == 0
    assert c.notes["CHG1"][-1].startswith("Pipeline")


def test_stale_blocks(data, tmp_path):
    c = FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})
    assert check_change("CHG1", c, data, root=tmp_path) == 1   # dort wurde nichts geschrieben
    assert "veraltet" in c.notes["CHG1"][-1]