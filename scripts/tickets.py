from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

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