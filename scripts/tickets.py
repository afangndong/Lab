from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests
import os

TABLE = "/api/now/table/change_request"

@dataclass
class Change:
    number: str
    short_description: str
    state: str


class TicketClient(ABC):
    """Die Schnittstelle: Die Pipeline kennt nur diese drei Methoden."""

    @abstractmethod
    def get_change(self, number: str) -> Change: ...
        

    @abstractmethod
    def add_note(self, number: str, text: str) -> None: ...

    @abstractmethod
    def set_state(self, number: str, state: str) -> None: ...


class FakeClient(TicketClient):
    """Speichert alles im Speicher, ohne Server. Nur für Tests."""

    def __init__(self, changes: dict):
        self.changes = changes
        self.notes = {}   # Ticketnummer -> Liste von Texten

    def get_change(self, number):
        eintrag = self.changes[number]        # wirft KeyError, wenn es die Nummer nicht gibt
        return Change(number, eintrag["short_description"], eintrag["state"])

    def add_note(self, number, text):
        self.notes.setdefault(number, []).append(text)

    def set_state(self, number, state):
        self.changes[number]["state"] = state


class ServiceNowClient(TicketClient):
    """Spricht mit ServiceNow (oder dem Mock) über die Table-API."""

    def __init__(self, base_url, session=None):
        self.base_url = base_url
        self.session = session or requests.Session()

    def _find(self, number):
        """Sucht das Ticket zur Nummer und gibt den rohen Eintrag zurück."""
        r = self.session.get(
            self.base_url + TABLE,
            params={"sysparm_query": f"number={number}"},
        )
        r.raise_for_status()
        result = r.json()["result"]
        if not result:
            raise KeyError(number)
        return result[0]

    def get_change(self, number):
        item = self._find(number)
        return Change(item["number"], item["short_description"], item["state"])

    def add_note(self, number, text):
        item = self._find(number)
        r = self.session.patch(
            self.base_url + TABLE + "/" + item["sys_id"],
            json={"work_notes": text},
        )
        r.raise_for_status()

    def set_state(self, number, state):
        item = self._find(number)
        r = self.session.patch(
            self.base_url + TABLE + "/" + item["sys_id"],
            json={"state": state},
        )
        r.raise_for_status()

# Redmine kennt keine Changes. Die Namen der Redmine-Status werden auf die
# Status der Pipeline abgebildet. Die Redmine-Status "Geplant", "Freigabe erforderlich",
# "Freigegeben" und "Abgelehnt" legst du in der Verwaltung selbst an.
REDMINE_STATUS_MAP = {
    "New": "new",
    "Geplant": "scheduled",
    "Freigabe erforderlich": "awaiting_approval",
    "Freigegeben": "approved",
    "Abgelehnt": "rejected",
    "Closed": "closed",
}


class RedmineClient(TicketClient):
    """Spricht mit Redmine über die REST-API. Die Ticketnummer ist die Ticket-ID (z. B. 12 oder #12)."""

    def __init__(self, base_url, api_key, session=None, status_map=None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update({"X-Redmine-API-Key": api_key})
        self.status_map = status_map or REDMINE_STATUS_MAP

    @staticmethod
    def _id(number):
        text = str(number).lstrip("#")
        if not text.isdigit():
            raise KeyError(number)
        return text

    def _issue_url(self, number):
        return f"{self.base_url}/issues/{self._id(number)}.json"

    def get_change(self, number):
        r = self.session.get(self._issue_url(number))
        if r.status_code == 404:
            raise KeyError(number)
        r.raise_for_status()
        issue = r.json()["issue"]
        name = issue["status"]["name"]
        state = self.status_map.get(name, name.lower())
        return Change(str(issue["id"]), issue["subject"], state)

    def add_note(self, number, text):
        r = self.session.put(self._issue_url(number), json={"issue": {"notes": text}})
        r.raise_for_status()

    def _status_id(self, state):
        """Sucht die Redmine-Status-ID zu einem Status der Pipeline."""
        name = {v: k for k, v in self.status_map.items()}.get(state, state)
        r = self.session.get(f"{self.base_url}/issue_statuses.json")
        r.raise_for_status()
        statuses = r.json()["issue_statuses"]
        for status in statuses:
            if status["name"].lower() == name.lower():
                return status["id"]
        bekannt = ", ".join(s["name"] for s in statuses)
        raise ValueError(f"Redmine kennt den Status '{name}' nicht (vorhanden: {bekannt})")

    def set_state(self, number, state):
        r = self.session.put(
            self._issue_url(number),
            json={"issue": {"status_id": self._status_id(state)}},
        )
        r.raise_for_status()


def client_from_env():
    """Baut den Ticket-Client aus der Umgebung.

    TICKET_SYSTEM=redmine: REDMINE_URL und REDMINE_API_KEY. Sonst ServiceNow (SERVICENOW_URL).
    """
    if os.environ.get("TICKET_SYSTEM", "servicenow") == "redmine":
        return RedmineClient(
            os.environ.get("REDMINE_URL", "http://localhost:3000"),
            os.environ["REDMINE_API_KEY"],
        )
    return ServiceNowClient(os.environ.get("SERVICENOW_URL", "http://localhost:8081"))