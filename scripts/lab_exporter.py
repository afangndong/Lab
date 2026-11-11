#!/usr/bin/env python3
"""Prometheus-Exporter für das Lab: OSPF-Nachbarn je Router und Erreichbarkeit zwischen Standorten.

Läuft auf dem Host (braucht `docker`) und misst bei jedem Abruf neu.
"""
import os
import sys
import time

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, GaugeMetricFamily

import netmodel
from verify import expected_neighbors, run


def count_full(ausgabe):
    """Zählt die OSPF-Nachbarn im Zustand Full aus der Ausgabe von `show ip ospf neighbor`."""
    return sum(1 for zeile in ausgabe.splitlines() if "Full/" in zeile)


class LabCollector:
    def __init__(self, data, run=run):
        self.data = data
        self.run = run

    def collect(self):
        full = GaugeMetricFamily("lab_ospf_neighbors_full",
                                 "OSPF-Nachbarn im Zustand Full", labels=["router"])
        expected = GaugeMetricFamily("lab_ospf_neighbors_expected",
                                     "Erwartete OSPF-Nachbarn", labels=["router"])
        for container, anzahl in expected_neighbors(self.data).items():
            router = container.removeprefix("lab-")
            rc, ausgabe = self.run(container, ["vtysh", "-c", "show ip ospf neighbor"])
            full.add_metric([router], count_full(ausgabe) if rc == 0 else 0)
            expected.add_metric([router], anzahl)
        yield full
        yield expected

        ping = GaugeMetricFamily("lab_ping_up",
                                 "1 = Server aus einer anderen Filiale erreichbar, 0 = nicht",
                                 labels=["quelle", "ziel"])
        hosts = netmodel.build_lab(self.data)["hosts"]
        clients = [h for h in hosts if h["role"] == "client"]
        servers = [h for h in hosts if h["role"] == "server"]
        for c in clients:
            for s in servers:
                if c["site"] == s["site"]:
                    continue
                rc, _ = self.run(c["container"], ["ping", "-c", "1", "-W", "1", s["ip"]])
                ping.add_metric([c["name"], s["name"]], 1 if rc == 0 else 0)
        yield ping


def main():
    port = int(os.environ.get("LAB_EXPORTER_PORT", "9101"))
    REGISTRY.register(LabCollector(netmodel.load()))
    start_http_server(port)        # lauscht auf 0.0.0.0, damit der Prometheus-Container zugreifen kann
    print(f"Lab-Exporter läuft auf Port {port} (Strg+C beendet)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())