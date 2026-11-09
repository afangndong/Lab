import netmodel
from tickets import FakeClient
from verify import check_ospf, check_pings, check_verification, expected_neighbors, main


def _ospf_ausgabe(anzahl):
    zeilen = ["Neighbor ID     Pri State           Up Time         Dead Time Address         Interface"]
    for i in range(anzahl):
        zeilen.append(f"10.255.0.{i + 2}       1 Full/Backup     1m00s             30.0s 10.0.1.{i + 2}      eth0:10.0.1.1")
    return "\n".join(zeilen)


def _fake_run(data, voll=None, ping_rc=0):
    """Täuscht Docker vor: OSPF-Ausgabe pro Container und einen festen Ping-Ergebnis-Code."""
    erwartet = expected_neighbors(data)
    erwartet.update(voll or {})

    def run(container, command):
        if command[0] == "vtysh":
            return 0, _ospf_ausgabe(erwartet[container])
        return ping_rc, ""

    return run


def _schnell(data, **kw):
    """Optionen ohne Wartezeit für die Tests."""
    return dict(run=_fake_run(data, **kw), ruhe=0, versuche=1, pause=0, sleep=lambda s: None)


def _ticket():
    return FakeClient({"CHG1": {"short_description": "x", "state": "scheduled"}})


def test_expected_neighbors(data):
    e = expected_neighbors(data)
    assert e["lab-core1"] == len(data["sites"])
    assert e["lab-br01"] == 1


def test_ospf_ok(data):
    assert check_ospf(expected_neighbors(data), _fake_run(data)) == []


def test_ospf_missing_neighbor(data):
    fehler = check_ospf(expected_neighbors(data), _fake_run(data, voll={"lab-br03": 0}))
    assert len(fehler) == 1
    assert "lab-br03" in fehler[0]


def test_pings_ok(data):
    hosts = netmodel.build_lab(data)["hosts"]
    assert check_pings(hosts, _fake_run(data)) == []


def test_pings_fail(data):
    hosts = netmodel.build_lab(data)["hosts"]
    fehler = check_pings(hosts, _fake_run(data, ping_rc=1))
    assert fehler
    assert "pc01" in fehler[0] or "pc03" in fehler[0]


def test_verification_ok(data):
    c = _ticket()
    assert check_verification("CHG1", c, data, **_schnell(data)) == 0
    assert c.notes["CHG1"][-1] == "Pipeline: Verifikation ok"


def test_verification_fails(data):
    c = _ticket()
    assert check_verification("CHG1", c, data, **_schnell(data, voll={"lab-br03": 0})) == 1
    assert "Verifikation fehlgeschlagen" in c.notes["CHG1"][-1]
    assert "lab-br03" in c.notes["CHG1"][-1]


def test_verification_retries_until_converged(data):
    """Beim ersten Versuch fehlt ein Nachbar, beim zweiten ist alles da."""
    zaehler = {"n": 0}
    gut = _fake_run(data)
    schlecht = _fake_run(data, voll={"lab-br03": 0})

    def run(container, command):
        if command[0] == "vtysh":
            zaehler["n"] += 1
        # die ersten 5 vtysh-Aufrufe (= erste Runde über 5 Router) sind schlecht
        return (schlecht if zaehler["n"] <= 5 else gut)(container, command)

    c = _ticket()
    assert check_verification("CHG1", c, data, run=run, ruhe=0, versuche=3, pause=0,
                              sleep=lambda s: None) == 0


def test_main_needs_one_argument():
    assert main([]) == 2