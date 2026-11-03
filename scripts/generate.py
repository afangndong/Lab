#!/usr/bin/env python3
"""Erzeugt aus data/sites.yml die abgeleiteten Dateien.

  docker-compose.yml               Lab mit Docker Compose
  ansible/inventory.yml            Inventar fuer Ansible
  terraform/lab.auto.tfvars.json   Variablen fuer die Terraform-Variante

make gen         schreibt die Dateien
make gen-check   bricht mit Exit-Code 1 ab, wenn sie nicht zu den Daten passen
"""
import argparse
import json
import sys

import yaml

import netmodel

HEADER = "# GENERIERT aus data/sites.yml durch scripts/generate.py. Nicht von Hand aendern.\n"
FRR_IMAGE = "${FRR_IMAGE:-frrouting/frr:v8.4.1}"
CLIENT_IMAGE = "${CLIENT_IMAGE:-nicolaka/netshoot:latest}"
SERVER_IMAGE = "${SERVER_IMAGE:-nginx:alpine}"


class _IndentedDumper(yaml.SafeDumper):
    """Rueckt Listen unter ihrem Schluessel ein (so erwartet es yamllint/ansible-lint)."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def _dump(obj):
    return yaml.dump(
        obj, Dumper=_IndentedDumper, sort_keys=False, default_flow_style=False, allow_unicode=True
    )


def render_compose(lab):
    services = {}
    for router in lab["routers"]:
        services[router["name"]] = {
            "image": FRR_IMAGE,
            "container_name": router["container"],
            "hostname": router["name"],
            "privileged": True,
            "sysctls": {"net.ipv4.ip_forward": "1"},
            "volumes": ["./docker/frr/daemons:/etc/frr/daemons:ro"],
            "networks": {a["network"]: {"ipv4_address": a["ip"]} for a in router["attachments"]},
        }
    for host in lab["hosts"]:
        service = {
            "container_name": host["container"],
            "hostname": host["name"],
            "cap_add": ["NET_ADMIN"],
            "networks": {host["network"]: {"ipv4_address": host["ip"]}},
        }
        if host["role"] == "client":
            service = {"image": CLIENT_IMAGE, "command": ["tail", "-f", "/dev/null"], **service}
        else:
            service = {"image": SERVER_IMAGE, **service}
        services[host["name"]] = service
    networks = {
        net["name"]: {"ipam": {"config": [{"subnet": net["subnet"], "gateway": net["gateway"]}]}}
        for net in lab["networks"]
    }
    return HEADER + _dump({"services": services, "networks": networks})


def render_inventory(lab):
    routers, clients, servers = {}, {}, {}
    for router in lab["routers"]:
        routers[router["name"]] = {
            "container": router["container"],
            "router_id": router["router_id"],
            "ospf_networks": router["ospf_networks"],
        }
    for host in lab["hosts"]:
        entry = {
            "container": host["container"],
            "host_ip": host["ip"],
            "lan_gateway": host["gateway"],
            "site": host["site"],
        }
        (clients if host["role"] == "client" else servers)[host["name"]] = entry
    inventory = {
        "all": {
            "vars": {
                "ansible_connection": "local",
                "ansible_python_interpreter": "{{ ansible_playbook_python }}",
            },
            "children": {
                "routers": {"hosts": routers},
                "clients": {"hosts": clients},
                "servers": {"hosts": servers},
            },
        }
    }
    return HEADER + "---\n" + _dump(inventory)


def render_tfvars(lab):
    payload = {
        "networks": lab["networks"],
        "routers": [
            {"name": r["name"], "container": r["container"], "attachments": r["attachments"]}
            for r in lab["routers"]
        ],
        "hosts": [
            {k: h[k] for k in ("name", "container", "role", "network", "ip")} for h in lab["hosts"]
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_all(data, root=netmodel.ROOT):
    lab = netmodel.build_lab(data)
    return {
        root / "docker-compose.yml": render_compose(lab),
        root / "ansible" / "inventory.yml": render_inventory(lab),
        root / "terraform" / "lab.auto.tfvars.json": render_tfvars(lab),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--check", action="store_true", help="nur pruefen, nichts schreiben")
    parser.add_argument("--data", default=None, help="Pfad zu sites.yml (Standard: data/sites.yml)")
    args = parser.parse_args(argv)

    data = netmodel.load(args.data) if args.data else netmodel.load()
    files = render_all(data)

    if args.check:
        stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            for path in stale:
                print(f"VERALTET: {path.relative_to(netmodel.ROOT)} passt nicht zu data/sites.yml (make gen)")
            return 1
        print("Generierte Dateien sind aktuell")
        return 0

    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"geschrieben: {path.relative_to(netmodel.ROOT)}")
    return 0


def stale_files(data, root=netmodel.ROOT):
    """Gibt die Dateien zurück, die nicht zu den Daten passen."""
    files = render_all(data, root)
    return [p for p, text in files.items()
            if not p.exists() or p.read_text(encoding="utf-8") != text]



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--check", action="store_true", help="nur pruefen, nichts schreiben")
    parser.add_argument("--data", default=None, help="Pfad zu sites.yml (Standard: data/sites.yml)")
    args = parser.parse_args(argv)

    data = netmodel.load(args.data) if args.data else netmodel.load()

    if args.check:
        stale = stale_files(data)
        if stale:
            for path in stale:
                print(f"VERALTET: {path.relative_to(netmodel.ROOT)} passt nicht zu data/sites.yml (make gen)")
            return 1
        print("Generierte Dateien sind aktuell")
        return 0

    for path, text in render_all(data).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"geschrieben: {path.relative_to(netmodel.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
