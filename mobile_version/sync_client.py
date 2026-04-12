import requests
import data.database as db
from data.models import Card, Deck
from datetime import datetime


class SyncClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def pull(self) -> None:
        """Replace local DB with data from desktop."""
        resp = requests.get(f"{self.base_url}/export", timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        # Wipe and re-import all decks (cascade deletes cards too)
        for deck in db.get_all_decks():
            db.delete_deck(deck.id)

        for d in payload["decks"]:
            db.create_deck(d["name"])

        all_decks = db.get_all_decks()
        deck_name_to_id = {d.name: d.id for d in all_decks}

        for c in payload["cards"]:
            desktop_decks = payload["decks"]
            deck_name = next((d["name"] for d in desktop_decks if d["id"] == c["deck_id"]), None)
            local_deck_id = deck_name_to_id.get(deck_name)
            if local_deck_id is None:
                continue
            card = Card(
                front=c["front"], back=c["back"],
                is_quiz=c["is_quiz"], memory_level=c["memory_level"],
                deck_id=local_deck_id,
                last_reviewed=datetime.fromisoformat(c["last_reviewed"]) if c["last_reviewed"] else None,
                review_count=c["review_count"],
            )
            db.create_card(card)

    def push(self) -> None:
        """Send local DB to desktop for merging."""
        decks = db.get_all_decks()
        cards = db.get_all_cards()
        payload = {
            "decks": [
                {"id": d.id, "name": d.name, "created_at": d.created_at.isoformat()}
                for d in decks
            ],
            "cards": [
                {
                    "id": c.id, "deck_id": c.deck_id,
                    "front": c.front, "back": c.back,
                    "is_quiz": c.is_quiz, "memory_level": c.memory_level,
                    "last_reviewed": c.last_reviewed.isoformat() if c.last_reviewed else None,
                    "review_count": c.review_count,
                    "created_at": c.created_at.isoformat(),
                }
                for c in cards
            ],
        }
        resp = requests.post(f"{self.base_url}/import", json=payload, timeout=10)
        resp.raise_for_status()
