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
        for d in payload.get("decks", []):
            existing = db.get_all_decks()
            ids = {deck.id for deck in existing}
            if d["id"] not in ids:
                db.create_deck(d["name"])
        for c in payload.get("cards", []):
            existing_cards = db.get_all_cards()
            existing_ids = {card.id for card in existing_cards}
            if c["id"] not in existing_ids:
                card = Card(
                    front=c["front"], back=c["back"],
                    is_quiz=c["is_quiz"], memory_level=c["memory_level"],
                    deck_id=c["deck_id"],
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
