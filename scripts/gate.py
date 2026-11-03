#!/usr/bin/env python3
"""Tor vor dem Rollout: Ticket prüfen, Daten validieren, Ergebnis ins Ticket."""
import os
import sys

import netmodel
from tickets import TicketClient, ServiceNowClient
from validate import validate
from generate import stale_files



APPROVED_STATE = "scheduled"


def check_change(number, client: TicketClient, data, root=netmodel.ROOT):
    try:
        change = client.get_change(number)
    except KeyError:
        print(f"Ticket {number} nicht gefunden")
        return 1

    if change.state != APPROVED_STATE:
        client.add_note(number, f"Pipeline: nicht freigegeben (Status: {change.state})")
        return 1

    fehler = validate(data)   # deine Validierung aus validate.py aufrufen
    if fehler:
        client.add_note(number, "Pipeline: Validierung fehlgeschlagen: " + "; ".join(fehler))
        return 1

    veraltet = stale_files(data, root)
    if veraltet:
        client.add_note(number, "Pipeline: generierte Dateien veraltet: "
                        + ", ".join(p.name for p in veraltet))
        return 1    

    client.add_note(number, "Pipeline: Validierung ok")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Aufruf: python scripts/gate.py CHG-Nummer")
        return 2

    url = os.environ.get("SERVICENOW_URL", "http://localhost:8081")
    client = ServiceNowClient(url)   #  ServiceNowClient mit der url anlegen
    data = netmodel.load()     # Daten mit netmodel.load() laden
    return check_change(argv[0], client, data)


if __name__ == "__main__":
    sys.exit(main())