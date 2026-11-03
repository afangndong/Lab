import netmodel

def test_helper_functions(data):
    s = data["sites"][0]                      # br01
    assert netmodel.core_ip(s) == "10.0.1.1"
    assert netmodel.branch_ip(s) == "10.0.1.2"
    assert netmodel.lan_gateway(s) == "10.10.1.254"
    assert netmodel.docker_gateway("10.10.1.0/24") == "10.10.1.253"

def test_core_router_first(data):
    lab = netmodel.build_lab(data)
    assert lab["routers"][0]["name"] == "core1"
    assert len(lab["routers"]) == 1 + len(data["sites"])

def test_core_attachments(data):
    core = netmodel.build_lab(data)["routers"][0]
    assert {"network": "bb1", "ip": "10.0.1.1"} in core["attachments"]
    assert len(core["attachments"]) == len(data["sites"])

def test_branch_router_br01(data):
    lab = netmodel.build_lab(data)
    br01 = next(r for r in lab["routers"] if r["name"] == "br01")
    assert br01["container"] == "lab-br01"
    assert br01["attachments"] == [
        {"network": "bb1", "ip": "10.0.1.2"},
        {"network": "lan1", "ip": "10.10.1.254"},
    ]

def test_networks_have_gateway(data):
    nets = {n["name"]: n for n in netmodel.build_lab(data)["networks"]}
    assert nets["bb1"]["gateway"] == "10.0.1.253"
    assert nets["lan1"]["gateway"] == "10.10.1.253"
    assert len(nets) == 2 * len(data["sites"])

def test_hosts(data):
    hosts = {h["name"]: h for h in netmodel.build_lab(data)["hosts"]}
    assert len(hosts) == 6
    assert hosts["pc01"]["network"] == "lan1"
    assert hosts["pc01"]["gateway"] == "10.10.1.254"
    assert hosts["srv-lager"]["role"] == "server"