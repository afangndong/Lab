from prometheus_client import CollectorRegistry, generate_latest

import netmodel
from lab_exporter import LabCollector, count_full
from verify import expected_neighbors


def _ospf_ausgabe(anzahl):
    zeilen = ["Neighbor ID     Pri State           Up Time         Dead Time Address         Interface"]
    for i in range(anzahl):
        zeilen.append(f"10.255.0.{i + 2}       1 Full/Backup     1m00s             30.0s 10.0.1.{i + 2}      eth0:10.0.1.1")
    return "\n".join(zeilen)


def _fake_run(data, voll=None, ping_ok=True, vtysh_rc=0):
    erwartet = expected_neighbors(data)
    erwartet.update(voll or {})

    def run(container, command):
        if command[0] == "vtysh":
            return vtysh_rc, _ospf_ausgabe(erwartet[container])
        return (0 if ping_ok else 1), ""

    return run


def _metrics(data, **kw):
    registry = CollectorRegistry()
    registry.register(LabCollector(data, run=_fake_run(data, **kw)))
    return generate_latest(registry).decode()


def test_count_full():
    assert count_full(_ospf_ausgabe(3)) == 3
    assert count_full("") == 0
    assert count_full("10.255.0.2  1 ExStart/Backup  1m  30s  10.0.1.2  eth0") == 0


def test_ospf_metrics_ok(data):
    text = _metrics(data)
    assert 'lab_ospf_neighbors_full{router="core1"} 4.0' in text
    assert 'lab_ospf_neighbors_expected{router="core1"} 4.0' in text
    assert 'lab_ospf_neighbors_full{router="br01"} 1.0' in text


def test_ospf_neighbor_missing(data):
    text = _metrics(data, voll={"lab-br03": 0})
    assert 'lab_ospf_neighbors_full{router="br03"} 0.0' in text
    assert 'lab_ospf_neighbors_expected{router="br03"} 1.0' in text


def test_vtysh_error_counts_as_zero(data):
    text = _metrics(data, vtysh_rc=1)
    assert 'lab_ospf_neighbors_full{router="br01"} 0.0' in text


def test_ping_metrics_ok(data):
    text = _metrics(data)
    assert 'lab_ping_up{quelle="pc01",ziel="srv-lager"} 1.0' in text
    assert 'lab_ping_up{quelle="pc03",ziel="srv01"} 1.0' in text


def test_ping_down(data):
    text = _metrics(data, ping_ok=False)
    assert 'lab_ping_up{quelle="pc01",ziel="srv-lager"} 0.0' in text


def test_no_pings_inside_same_site(data):
    text = _metrics(data)
    hosts = netmodel.build_lab(data)["hosts"]
    clients = {h["name"]: h["site"] for h in hosts if h["role"] == "client"}
    servers = {h["name"]: h["site"] for h in hosts if h["role"] == "server"}
    erwartet = sum(1 for c in clients.values() for s in servers.values() if c != s)
    assert text.count("lab_ping_up{") == erwartet