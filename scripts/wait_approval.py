#!/usr/bin/env python3
"""Freigabe über das Ticket: Plan melden, Status setzen und warten, bis ein Mensch entscheidet."""
import os
import sys
import time

from tickets import TicketClient, client_from_env

AWAITING = "awaiting_approval"
APPROVED = "approved"
REJECTED = "rejected"


def wait_for_approval(number, client: TicketClient, timeout=3600, interval=10,
                      sleep=time.sleep, clock=time.monotonic):
    """Gibt 0 zurück bei Freigabe, 1 bei Ablehnung oder wenn die Zeit abläuft."""
    client.add_note(number, "Pipeline: Plan liegt vor, Freigabe im Ticket erforderlich "
                            f"(Status auf '{APPROVED}' setzen, zum Ablehnen auf '{REJECTED}')")
    client.set_state(number, AWAITING)

    ende = clock() + timeout
    while clock() < ende:
        state = client.get_change(number).state
        if state == APPROVED:
            client.add_note(number, "Pipeline: Freigabe im Ticket erteilt")
            return 0
        if state == REJECTED:
            client.add_note(number, "Pipeline: Freigabe im Ticket abgelehnt, Rollout wird nicht ausgeführt")
            return 1
        sleep(interval)

    client.add_note(number, f"Pipeline: keine Freigabe innerhalb von {timeout // 60} Minuten, abgebrochen")
    return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Aufruf: python scripts/wait_approval.py CHG-Nummer")
        return 2
    timeout = int(os.environ.get("APPROVAL_TIMEOUT_MIN", "60")) * 60
    interval = int(os.environ.get("APPROVAL_INTERVAL_SEC", "10"))
    return wait_for_approval(argv[0], client_from_env(), timeout=timeout, interval=interval)


if __name__ == "__main__":
    sys.exit(main())