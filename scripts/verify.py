#!/usr/bin/env python3
"""Verifikation nach dem Rollout: OSPF-Nachbarn und Erreichbarkeit prüfen, Ergebnis ins Ticket."""
import subprocess
import sys
import time

import netmodel
from tickets import TicketClient, client_from_env


def run(container, command):
    """Führt einen Befehl im Container aus. Gibt (Exit-Code, Ausgabe) zurück."""
    r = subprocess.run(["docker", "exec", container] + command, capture_output=True, text=True)
    return r.returncode, r.stdout


def expected_neighbors(data):
    """core1 hat einen Nachbarn pro Filiale, jede Filiale hat nur core1."""
    kern = data["core"]["name"]
    erwartet = {}
    for router in netmodel.build_lab(data)["routers"]:
        erwartet[router["container"]] = len(data["sites"]) if router["name"] == kern else 1
    return erwartet


def check_ospf(erwartet, run=run):
    fehler = []
    for container, anzahl in erwartet.items():
        rc, ausgabe = run(container, ["vtysh", "-c", "show ip ospf neighbor"])
        voll = sum(1 for zeile in ausgabe.splitlines() if "Full/" in zeile)
        if rc != 0 or voll != anzahl:
            fehler.append(f"{container}: {voll} von {anzahl} OSPF-Nachbarn im Zustand Full")
    return fehler


def check_pings(hosts, run=run):
    """Jeder Client muss jeden Server in einer anderen Filiale erreichen."""
    fehler = []
    clients = [h for h in hosts if h["role"] == "client"]
    servers = [h for h in hosts if h["role"] == "server"]
    for c in clients:
        for s in servers:
            if c["site"] == s["site"]:
                continue
            rc, _ = run(c["container"], ["ping", "-c", "2", "-W", "2", s["ip"]])
            if rc != 0:
                fehler.append(f"{c['name']} erreicht {s['name']} ({s['ip']}) nicht")
    return fehler


def verify(data, run=run, ruhe=45, versuche=18, pause=5, sleep=time.sleep):
    """Wartet zuerst `ruhe` Sekunden (OSPF-Dead-Interval 40 s), damit ein Fehler
    sichtbar wird, und prüft dann bis zu `versuche` Mal. Gibt die Fehlerliste zurück."""
    erwartet = expected_neighbors(data)
    hosts = netmodel.build_lab(data)["hosts"]
    sleep(ruhe)
    fehler = []
    for versuch in range(versuche):
        fehler = check_ospf(erwartet, run) + check_pings(hosts, run)
        if not fehler:
            return []
        if versuch < versuche - 1:
            sleep(pause)
    return fehler


def check_verification(number, client: TicketClient, data, **optionen):
    fehler = verify(data, **optionen)
    if fehler:
        client.add_note(number, "Pipeline: Verifikation fehlgeschlagen: " + "; ".join(fehler))
        return 1
    client.add_note(number, "Pipeline: Verifikation ok")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Aufruf: python scripts/verify.py CHG-Nummer")
        return 2
    return check_verification(argv[0], client_from_env(), netmodel.load())


if __name__ == "__main__":
    sys.exit(main())