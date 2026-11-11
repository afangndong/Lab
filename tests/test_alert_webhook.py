import alert_webhook as w
from tickets import FakeClient
from fastapi.testclient import TestClient


def alarm(status="firing", fp="f1"):
    return {"alerts": [{"status": status, "fingerprint": fp,
                        "labels": {"alertname": "OspfNachbarFehlt", "router": "br03"},
                        "annotations": {"summary": "OSPF auf br03: Nachbarn fehlen",
                                        "description": "zu wenige"},
                        "startsAt": "t0", "endsAt": "t1"}]}


def setup_function():
    w.TICKETS.clear()


def test_firing_legt_ein_ticket_an():
    c = FakeClient({})
    assert w.verarbeite(alarm(), c)[0].startswith("angelegt")
    (eintrag,) = c.changes.values()
    assert eintrag["short_description"] == "[Alarm] OSPF auf br03: Nachbarn fehlen"
    assert "router: br03" in eintrag["description"]


def test_wiederholung_legt_kein_zweites_ticket_an():
    c = FakeClient({})
    w.verarbeite(alarm(), c)
    assert w.verarbeite(alarm(), c) == []
    assert len(c.changes) == 1


def test_resolved_schreibt_notiz():
    c = FakeClient({})
    w.verarbeite(alarm(), c)
    nummer = next(iter(c.changes))
    assert w.verarbeite(alarm("resolved"), c)[0].startswith("behoben")
    assert "Alarm behoben" in c.notes[nummer][0]


def test_resolved_ohne_ticket_wird_ignoriert():
    assert w.verarbeite(alarm("resolved"), FakeClient({})) == []


def test_endpunkt(monkeypatch):
    c = FakeClient({})
    monkeypatch.setattr(w, "_client", c)
    r = TestClient(w.app).post("/alert", json=alarm())
    assert r.status_code == 200 and len(c.changes) == 1