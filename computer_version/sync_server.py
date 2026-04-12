"""
Run with: python sync_server.py
Listens on 0.0.0.0:5000. Phone connects to http://<your-mac-ip>:5000
"""
from flask import Flask, jsonify, request
import computer_version.data.database as db
from computer_version.data.models import Card, Deck
from datetime import datetime


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/export")
    def export():
        decks = db.get_all_decks()
        cards = db.get_all_cards()
        return jsonify({
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
        })

    @app.route("/import", methods=["POST"])
    def import_data():
        payload = request.get_json(force=True)

        # Build existing deck id set once
        existing_decks = {deck.id: deck for deck in db.get_all_decks()}

        # Map phone deck id -> desktop deck id
        deck_id_map = {}
        for d in payload.get("decks", []):
            if d["id"] in existing_decks:
                # Deck already exists on desktop — map to same id
                deck_id_map[d["id"]] = d["id"]
            else:
                # New deck — find match by name or create
                name_match = next((dk for dk in existing_decks.values() if dk.name == d["name"]), None)
                if name_match:
                    deck_id_map[d["id"]] = name_match.id
                else:
                    new_deck = db.create_deck(d["name"])
                    deck_id_map[d["id"]] = new_deck.id
                    existing_decks[new_deck.id] = new_deck

        # Import cards using remapped deck ids
        existing_card_ids = {card.id for card in db.get_all_cards()}
        for c in payload.get("cards", []):
            if c["id"] in existing_card_ids:
                continue
            local_deck_id = deck_id_map.get(c["deck_id"])
            if local_deck_id is None:
                continue  # skip orphaned card
            card = Card(
                front=c["front"], back=c["back"],
                is_quiz=c["is_quiz"], memory_level=c["memory_level"],
                deck_id=local_deck_id,
                last_reviewed=datetime.fromisoformat(c["last_reviewed"]) if c["last_reviewed"] else None,
                review_count=c["review_count"],
            )
            db.create_card(card)

        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    db.init_db()
    app = create_app()
    print("Sync server running on port 5000")
    print("Connect phone to: http://<this-machine-ip>:5000")
    app.run(host="0.0.0.0", port=5000)
