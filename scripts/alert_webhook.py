"""Empfängt Alertmanager-Webhooks und legt für jeden Alarm ein Ticket an.

Start: uvicorn alert_webhook:app --app-dir scripts --host 0.0.0.0 --port 9102
Ticket-System kommt aus der Umgebung (siehe tickets.client_from_env).

Grenze: Die Zuordnung Alarm -> Ticket liegt nur im Speicher. Nach einem Neustart
des Webhooks entsteht bei einem noch feuernden Alarm ein neues Ticket.
"""
from fastapi import FastAPI, Request

from tickets import client_from_env

app = FastAPI()
TICKETS: dict[str, str] = {}      # fingerprint -> Ticketnummer
_client = None


def get_client():
    global _client
    if _client is None:
        _client = client_from_env()
    return _client


def beschreibung(alert: dict) -> str:
    labels = alert.get("labels", {})
    ann = alert.get("annotations", {})
    zeilen = [ann.get("description", ""), "", "Labels:"]
    zeilen += [f"- {k}: {v}" for k, v in sorted(labels.items())]
    zeilen.append(f"Beginn: {alert.get('startsAt', '?')}")
    return "\n".join(zeilen).strip()


def verarbeite(payload: dict, client) -> list[str]:
    """Verarbeitet eine Alertmanager-Nachricht, gibt die Aktionen als Text zurück."""
    aktionen = []
    for alert in payload.get("alerts", []):
        fp = alert.get("fingerprint") or alert["labels"].get("alertname", "?")
        if alert.get("status") == "firing":
            if fp in TICKETS:
                continue                                  # schon ein Ticket vorhanden
            titel = alert.get("annotations", {}).get("summary") \
                or alert["labels"].get("alertname", "Alarm")
            TICKETS[fp] = client.create_change(f"[Alarm] {titel}", beschreibung(alert))
            aktionen.append(f"angelegt {TICKETS[fp]}")
        elif alert.get("status") == "resolved" and fp in TICKETS:
            nummer = TICKETS.pop(fp)
            client.add_note(nummer, f"Alarm behoben (Ende: {alert.get('endsAt', '?')}). "
                                    "Ticket bitte prüfen und schließen.")
            aktionen.append(f"behoben {nummer}")
    return aktionen


@app.post("/alert")
async def alert(request: Request):
    payload = await request.json()
    return {"aktionen": verarbeite(payload, get_client())}


@app.get("/health")
def health():
    return {"ok": True}