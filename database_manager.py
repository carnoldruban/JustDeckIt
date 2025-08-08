import sqlite3
import json
from datetime import datetime

class DBManager:
    def __init__(self, db_path="blackjack_data.db"):
        """Initializes the database connection and creates tables if they don't exist."""
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            print(f"Successfully connected to database at {self.db_path}")
            self.create_tables()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")

    def create_tables(self):
        """Creates the normalized database schema."""
        if not self.conn:
            print("Cannot create tables, no database connection.")
            return

        cursor = self.conn.cursor()

        # Table for game rounds
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id_str TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL
        );
        """)

        # Table for hands within a round
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            seat_num INTEGER NOT NULL, -- -1 for dealer
            final_score INTEGER,
            result TEXT,
            FOREIGN KEY (round_id) REFERENCES game_rounds (id)
        );
        """)

        # Table for individual cards in each hand
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hand_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_id INTEGER NOT NULL,
            card_value TEXT NOT NULL,
            FOREIGN KEY (hand_id) REFERENCES hands (id)
        );
        """)

        self.conn.commit()
        print("Normalized tables created successfully or already exist.")

    def save_game_state(self, payload):
        """Saves a complete game state from a JSON payload into the normalized tables."""
        if not self.conn:
            return

        game_id_str = payload.get('gameId')
        if not game_id_str:
            return

        cursor = self.conn.cursor()

        # --- 1. Upsert Game Round ---
        timestamp = datetime.now().isoformat()
        cursor.execute("INSERT OR IGNORE INTO game_rounds (game_id_str, timestamp) VALUES (?, ?)", (game_id_str, timestamp))

        # Get the round's primary key
        cursor.execute("SELECT id FROM game_rounds WHERE game_id_str = ?", (game_id_str,))
        round_row = cursor.fetchone()
        if not round_row: return
        round_id = round_row[0]

        # --- 2. Clear old data for this round to prevent duplicates on updates ---
        # Get all hand_ids associated with this round_id
        cursor.execute("SELECT id FROM hands WHERE round_id = ?", (round_id,))
        old_hand_ids = cursor.fetchall()
        if old_hand_ids:
            # Flatten the list of tuples
            ids_to_delete = [h[0] for h in old_hand_ids]
            # Delete cards associated with those hands
            cursor.execute(f"DELETE FROM hand_cards WHERE hand_id IN ({','.join('?' for _ in ids_to_delete)})", ids_to_delete)
        # Delete the hands themselves
        cursor.execute("DELETE FROM hands WHERE round_id = ?", (round_id,))


        # --- 3. Insert Dealer Hand ---
        dealer_hand = payload.get('dealer')
        if dealer_hand:
            cursor.execute("INSERT INTO hands (round_id, seat_num, final_score, result) VALUES (?, ?, ?, ?)",
                           (round_id, -1, dealer_hand.get('score'), dealer_hand.get('result')))
            dealer_hand_id = cursor.lastrowid
            for card in dealer_hand.get('cards', []):
                cursor.execute("INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                               (dealer_hand_id, card.get('value')))

        # --- 4. Insert Player Hands ---
        seats = payload.get('seats', {})
        for seat_num, seat_data in seats.items():
            hand_data = seat_data.get('first')
            if hand_data:
                cursor.execute("INSERT INTO hands (round_id, seat_num, final_score, result) VALUES (?, ?, ?, ?)",
                               (round_id, int(seat_num), hand_data.get('score'), hand_data.get('result')))
                player_hand_id = cursor.lastrowid
                for card in hand_data.get('cards', []):
                    cursor.execute("INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                                   (player_hand_id, card.get('value')))

        self.conn.commit()
        print(f"Successfully saved game state for round {game_id_str}")


    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    db = DBManager()
    # The tables are created on initialization now.
    db.close()
