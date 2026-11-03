#!/usr/bin/env python3
"""Gemeinsames Datenmodell: liest data/sites.yml und leitet daraus das Lab ab."""
import ipaddress
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "sites.yml"


def load(path=DATA_FILE):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _net(value):
    return ipaddress.ip_network(value, strict=True)


def core_ip(site):
    """Backbone-Adresse von core1: .1"""
    return str(_net(site["backbone"]).network_address + 1)


def branch_ip(site):
    """Backbone-Adresse der Filiale: .2"""
    return str(_net(site["backbone"]).network_address + 2)


def lan_gateway(site):
    """Router im Filial-LAN: vorletzte Adresse, z. B. 10.10.1.254"""
    return str(_net(site["lan"]).broadcast_address - 1)


def docker_gateway(network):
    """Adresse der Docker-Bridge (Host-Seite): drittletzte Adresse, z. B. .253"""
    return str(_net(network).broadcast_address - 2)


def build_lab(data):
    """Leitet Netze, Router und Hosts des Labs aus den Standortdaten ab."""
    networks, routers, hosts = [], [], []
    core = data["core"]
    core_attachments, core_ospf = [], []

    for site in data["sites"]:
        backbone_net = f"bb{site['id']}"
        lan_net = f"lan{site['id']}"
        networks.append(
            {"name": backbone_net, "subnet": site["backbone"], "gateway": docker_gateway(site["backbone"])}
        )
        networks.append({"name": lan_net, "subnet": site["lan"], "gateway": docker_gateway(site["lan"])})

        core_attachments.append({"network": backbone_net, "ip": core_ip(site)})
        core_ospf.append(site["backbone"])

        routers.append(
            {
                "name": site["name"],
                "container": f"lab-{site['name']}",
                "router_id": site["router_id"],
                "attachments": [
                    {"network": backbone_net, "ip": branch_ip(site)},
                    {"network": lan_net, "ip": lan_gateway(site)},
                ],
                "ospf_networks": [site["backbone"], site["lan"]],
            }
        )
        for host in site.get("hosts") or []:
            hosts.append(
                {
                    "name": host["name"],
                    "container": f"lab-{host['name']}",
                    "role": host["role"],
                    "site": site["name"],
                    "network": lan_net,
                    "ip": host["ip"],
                    "gateway": lan_gateway(site),
                }
            )

    routers.insert(
        0,
        {
            "name": core["name"],
            "container": f"lab-{core['name']}",
            "router_id": core["router_id"],
            "attachments": core_attachments,
            "ospf_networks": core_ospf,
        },
    )
    return {"networks": networks, "routers": routers, "hosts": hosts}
