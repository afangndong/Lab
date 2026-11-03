#!/usr/bin/env python3
"""Prueft data/sites.yml: Struktur, Namen, Subnetze, IPs und SLA-Klassen.

Exit-Code 1 bei Fehlern, damit die Pipeline vor dem Rollout abbricht.
"""
import ipaddress
import re
import sys

import yaml

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,19}$")
ROLES = {"client", "server"}


def _parse_net(value, label, what, errors):
    if not isinstance(value, str):
        errors.append(f"{label}: ungueltiges Subnetz fuer {what} ({value!r})")
        return None
    try:
        net = ipaddress.ip_network(value, strict=True)
    except ValueError as exc:
        errors.append(f"{label}: ungueltiges Subnetz fuer {what} ({exc})")
        return None
    if net.version != 4 or not 16 <= net.prefixlen <= 28:
        errors.append(f"{label}: {what} {net} muss ein IPv4-Netz zwischen /16 und /28 sein")
        return None
    return net


def validate(data):
    """Gibt eine Liste von Fehlertexten zurueck (leer = alles gueltig)."""
    if not isinstance(data, dict):
        return ["Datei ist leer oder kein Mapping"]

    errors = []
    core = data.get("core") or {}
    classes = data.get("sla_classes") or {}
    sites = data.get("sites") or []

    names = {}
    router_ids = {}
    site_ids = {}
    nets = []
    host_ips = {}

    def register_name(name, label):
        if not isinstance(name, str) or not NAME_RE.match(name):
            errors.append(f"{label}: ungueltiger Name {name!r} (klein, 2-20 Zeichen, a-z 0-9 -)")
            return
        if name in names:
            errors.append(f"{label}: Name {name} doppelt (schon bei {names[name]})")
        names[name] = label

    def register_router_id(value, label):
        try:
            rid = str(ipaddress.IPv4Address(value))
        except ValueError:
            errors.append(f"{label}: ungueltige router_id {value!r}")
            return
        if rid in router_ids:
            errors.append(f"{label}: router_id {rid} doppelt (schon bei {router_ids[rid]})")
        router_ids[rid] = label

    register_name(core.get("name"), "core")
    register_router_id(core.get("router_id"), "core")

    if not classes:
        errors.append("sla_classes: mindestens eine Klasse noetig")
    for cname, cfg in classes.items():
        latency = (cfg or {}).get("max_latency_ms")
        if not isinstance(latency, (int, float)) or isinstance(latency, bool) or latency <= 0:
            errors.append(f"sla_classes/{cname}: max_latency_ms muss eine Zahl > 0 sein")

    if not sites:
        errors.append("sites: mindestens ein Standort noetig")

    for site in sites:
        if not isinstance(site, dict):
            errors.append(f"Standort {site!r}: muss ein Mapping sein")
            continue
        label = str(site.get("name", "?"))
        register_name(site.get("name"), label)

        sid = site.get("id")
        if not isinstance(sid, int) or isinstance(sid, bool) or not 1 <= sid <= 250:
            errors.append(f"{label}: id {sid!r} muss eine ganze Zahl von 1 bis 250 sein")
        elif sid in site_ids:
            errors.append(f"{label}: id {sid} doppelt (schon bei {site_ids[sid]})")
        else:
            site_ids[sid] = label

        register_router_id(site.get("router_id"), label)

        if site.get("sla") not in classes:
            errors.append(f"{label}: SLA-Klasse {site.get('sla')!r} nicht definiert")

        lan_net = None
        for what in ("backbone", "lan"):
            net = _parse_net(site.get(what), label, what, errors)
            if net is None:
                continue
            for other, other_label in nets:
                if net.overlaps(other):
                    errors.append(f"{label}: {what} {net} ueberlappt mit {other} ({other_label})")
            nets.append((net, f"{label}/{what}"))
            if what == "lan":
                lan_net = net

        for host in site.get("hosts") or []:
            hname = host.get("name") if isinstance(host, dict) else None
            hlabel = f"{label}/{hname}"
            if not isinstance(host, dict):
                errors.append(f"{label}: Host-Eintrag {host!r} muss ein Mapping sein")
                continue
            register_name(hname, hlabel)
            if host.get("role") not in ROLES:
                errors.append(f"{hlabel}: Rolle {host.get('role')!r} unbekannt (erlaubt: client, server)")
            try:
                ip = ipaddress.IPv4Address(host.get("ip"))
            except ValueError:
                errors.append(f"{hlabel}: ungueltige IP {host.get('ip')!r}")
                continue
            if lan_net is not None:
                if ip not in lan_net:
                    errors.append(f"{hlabel}: IP {ip} liegt nicht in {lan_net}")
                reserved = {
                    lan_net.network_address,
                    lan_net.broadcast_address,
                    lan_net.broadcast_address - 1,
                    lan_net.broadcast_address - 2,
                }
                if ip in reserved:
                    errors.append(f"{hlabel}: IP {ip} ist reserviert (Netz, Broadcast, Router oder Docker-Bridge)")
            if str(ip) in host_ips:
                errors.append(f"{hlabel}: IP {ip} doppelt (schon bei {host_ips[str(ip)]})")
            host_ips[str(ip)] = hlabel

    return errors


def main(path="data/sites.yml"):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FEHLER: {error}")
        sys.exit(1)
    print("Daten gueltig")


if __name__ == "__main__":
    main(*sys.argv[1:])