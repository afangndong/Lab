from abc import ABC, abstractmethod
from dataclasses import dataclass


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