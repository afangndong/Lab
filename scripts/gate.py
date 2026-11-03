#!/usr/bin/env python3
"""Tor vor dem Rollout: Ticket prüfen, Daten validieren, Ergebnis ins Ticket."""
from tickets import TicketClient
from validate import validate

APPROVED_STATE = "scheduled"


def check_change(number, client: TicketClient, data):
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

    client.add_note(number, "Pipeline: Validierung ok")
    return 0