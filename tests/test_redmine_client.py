from tickets import FakeClient
from wait_approval import main, wait_for_approval


def _ticket(state="scheduled"):
    return FakeClient({"CHG1": {"short_description": "x", "state": state}})


class Uhr:
    """Falsche Uhr: sleep() lässt die Zeit vorrücken und führt optional eine Aktion aus."""

    def __init__(self, aktion=None):
        self.jetzt = 0
        self.aufrufe = 0
        self.aktion = aktion

    def clock(self):
        return self.jetzt

    def sleep(self, sekunden):
        self.aufrufe += 1
        self.jetzt += sekunden
        if self.aktion:
            self.aktion(self.aufrufe)


def test_sets_awaiting_and_notes_first():
    c = _ticket()
    uhr = Uhr()
    wait_for_approval("CHG1", c, timeout=0, sleep=uhr.sleep, clock=uhr.clock)
    assert "Freigabe im Ticket erforderlich" in c.notes["CHG1"][0]
    assert c.get_change("CHG1").state == "awaiting_approval"


def test_approved_after_some_polls():
    c = _ticket()
    uhr = Uhr(aktion=lambda n: c.set_state("CHG1", "approved") if n == 3 else None)
    assert wait_for_approval("CHG1", c, timeout=600, interval=10,
                             sleep=uhr.sleep, clock=uhr.clock) == 0
    assert uhr.aufrufe == 3
    assert c.notes["CHG1"][-1] == "Pipeline: Freigabe im Ticket erteilt"


def test_rejected():
    c = _ticket()
    uhr = Uhr(aktion=lambda n: c.set_state("CHG1", "rejected"))
    assert wait_for_approval("CHG1", c, timeout=600, sleep=uhr.sleep, clock=uhr.clock) == 1
    assert "abgelehnt" in c.notes["CHG1"][-1]


def test_other_states_are_ignored():
    c = _ticket()
    uhr = Uhr(aktion=lambda n: c.set_state("CHG1", "approved") if n == 5 else c.set_state("CHG1", "new"))
    assert wait_for_approval("CHG1", c, timeout=600, sleep=uhr.sleep, clock=uhr.clock) == 0


def test_timeout():
    c = _ticket()
    uhr = Uhr()
    assert wait_for_approval("CHG1", c, timeout=120, interval=10,
                             sleep=uhr.sleep, clock=uhr.clock) == 1
    assert "keine Freigabe innerhalb von 2 Minuten" in c.notes["CHG1"][-1]
    assert uhr.aufrufe == 12


def test_main_needs_one_argument():
    assert main([]) == 2