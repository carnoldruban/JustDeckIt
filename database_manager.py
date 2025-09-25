import sqlite3
import json
import threading
import os
from datetime import datetime
from typing import Dict, Optional
from logging_config import get_logger, log_performance

class DatabaseManager:
    def __init__(self, db_name="blackjack_data.db"):
        self.logger = get_logger("DatabaseManager")
        # Store database files in the data directory
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        self.db_name = os.path.join(data_dir, db_name)
        self.lock = threading.Lock()
        self.round_counters = {}  # Track round numbers per shoe
        self.logger.info("Initializing DB: %s", db_name)
        self.create_tables()
        # Clear shoe_cards on startup per request to avoid stale state
        try:
            with self.lock:
                with self.get_connection() as conn:
                    conn.execute("DELETE FROM shoe_cards")
                    conn.commit()
            self.logger.info("Cleared shoe_cards table on initialization")
        except Exception as e:
            self.logger.error("Failed to clear shoe_cards on init: %s", e)

    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    @log_performance
    def create_tables(self):
        self.logger.info("Creating database tables")
        with self.lock:
            self.logger.info("Acquired lock for table creation")
            with self.get_connection() as conn:
                
                cursor = conn.cursor()
                # Create rounds table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rounds (
                        game_id TEXT,
                        shoe_name TEXT,
                        round_number INTEGER,
                        dealer_hand TEXT,
                        dealer_score TEXT,
                        seat0_hand TEXT DEFAULT '[]', seat0_score TEXT DEFAULT 'N/A', seat0_state TEXT DEFAULT 'Empty',
                        seat1_hand TEXT DEFAULT '[]', seat1_score TEXT DEFAULT 'N/A', seat1_state TEXT DEFAULT 'Empty',
                        seat2_hand TEXT DEFAULT '[]', seat2_score TEXT DEFAULT 'N/A', seat2_state TEXT DEFAULT 'Empty',
                        seat3_hand TEXT DEFAULT '[]', seat3_score TEXT DEFAULT 'N/A', seat3_state TEXT DEFAULT 'Empty',
                        seat4_hand TEXT DEFAULT '[]', seat4_score TEXT DEFAULT 'N/A', seat4_state TEXT DEFAULT 'Empty',
                        seat5_hand TEXT DEFAULT '[]', seat5_score TEXT DEFAULT 'N/A', seat5_state TEXT DEFAULT 'Empty',
                        seat6_hand TEXT DEFAULT '[]', seat6_score TEXT DEFAULT 'N/A', seat6_state TEXT DEFAULT 'Empty',
                        last_updated TIMESTAMP,
                        PRIMARY KEY (game_id, shoe_name)
                    )
                """)
                # Create shoe_cards table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shoe_cards (
                        shoe_name TEXT PRIMARY KEY,
                        undealt_cards TEXT NOT NULL,
                        dealt_cards TEXT NOT NULL
                    )
                """)
                
                # Create analytics tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shoe_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shoe_name TEXT NOT NULL,
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        final_stats TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prediction_validation (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        round_id INTEGER,
                        card_position INTEGER,
                        predicted_card TEXT,
                        actual_card TEXT,
                        position_offset INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS card_tracking (
                        tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        round_number INTEGER,
                        card_value TEXT,
                        position INTEGER,
                        seat_number INTEGER,
                        card_type TEXT,
                        sequence_number INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS seat_performance (
                        performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        seat_number INTEGER,
                        total_hands INTEGER,
                        wins INTEGER,
                        losses INTEGER,
                        pushes INTEGER,
                        win_rate REAL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.ensure_shoe_cards_columns()
                conn.commit()
                self.logger.info("Database tables created successfully")

    @log_performance
    def log_round_update(self, shoe_name, round_data):
        game_id = round_data.get('gameId')
        if not game_id:
            self.logger.warning("No game ID in round data")
            return
        
        try:
            with self.lock:
                # Keep round number stable per (shoe_name, game_id)
                if shoe_name not in self.round_counters:
                    self.round_counters[shoe_name] = {}
                if game_id not in self.round_counters[shoe_name]:
                    # First time we see this game_id for this shoe, assign next round index
                    next_round = max(self.round_counters[shoe_name].values(), default=0) + 1
                    self.round_counters[shoe_name][game_id] = next_round
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    data_to_log = {
                        "game_id": game_id,
                        "shoe_name": shoe_name,
                        "round_number": self.round_counters[shoe_name][game_id],
                        "last_updated": datetime.now()
                    }
                    
                    # Extract dealer data
                    if 'dealer' in round_data:
                        dealer = round_data['dealer']
                        # Filter hidden downcard "**" from printout while keeping raw data in DB
                        dealer_cards_raw = dealer.get('cards', [])
                        data_to_log["dealer_hand"] = json.dumps(dealer_cards_raw)
                        data_to_log["dealer_score"] = str(dealer.get('score', 0))
                        dealer_print_vals = [c.get('value') for c in dealer_cards_raw if isinstance(c, dict) and c.get('value') and c.get('value') != '**']
                        print(f"[DB] Dealer: score={data_to_log['dealer_score']} cards={dealer_print_vals}")
                    
                    # Initialize all seats to empty first
                    for i in range(7):
                        data_to_log[f"seat{i}_hand"] = '[]'
                        data_to_log[f"seat{i}_score"] = 'N/A'
                        data_to_log[f"seat{i}_state"] = 'Empty'
                    
                    # Extract seat data (this will overwrite the empty defaults for occupied seats)
                    if 'seats' in round_data:
                        for seat_num in range(7):
                            seat_key = str(seat_num)
                            if seat_key in round_data['seats']:
                                seat = round_data['seats'][seat_key]
                                if 'first' in seat:
                                    first = seat['first']
                                    # Keep raw cards in DB, but filter "**" in printouts
                                    raw_cards = first.get('cards', [])
                                    data_to_log[f"seat{seat_num}_hand"] = json.dumps(raw_cards)
                                    data_to_log[f"seat{seat_num}_score"] = str(first.get('score', 0))
                                    data_to_log[f"seat{seat_num}_state"] = first.get('state', 'unknown')
                                    seat_print_vals = [c.get('value') for c in raw_cards if isinstance(c, dict) and c.get('value') and c.get('value') != '**']
                                    print(f"[DB] Seat{seat_num}: score={data_to_log[f'seat{seat_num}_score']} state={data_to_log[f'seat{seat_num}_state']} cards={seat_print_vals}")
                                        
                    # Insert into database
                    cursor.execute("""
                        INSERT OR REPLACE INTO rounds (
                            game_id, shoe_name, round_number,
                            dealer_hand, dealer_score,
                            seat0_hand, seat0_score, seat0_state,
                            seat1_hand, seat1_score, seat1_state,
                            seat2_hand, seat2_score, seat2_state,
                            seat3_hand, seat3_score, seat3_state,
                            seat4_hand, seat4_score, seat4_state,
                            seat5_hand, seat5_score, seat5_state,
                            seat6_hand, seat6_score, seat6_state,
                            last_updated
                        ) VALUES (
                            :game_id, :shoe_name, :round_number,
                            :dealer_hand, :dealer_score,
                            :seat0_hand, :seat0_score, :seat0_state,
                            :seat1_hand, :seat1_score, :seat1_state,
                            :seat2_hand, :seat2_score, :seat2_state,
                            :seat3_hand, :seat3_score, :seat3_state,
                            :seat4_hand, :seat4_score, :seat4_state,
                            :seat5_hand, :seat5_score, :seat5_state,
                            :seat6_hand, :seat6_score, :seat6_state,
                            :last_updated
                        )
                    """, data_to_log)
                    
                    conn.commit()
                    self.logger.debug("Logged round update for game %s, round %d", game_id, self.round_counters[shoe_name][game_id])
                    
        except Exception as e:
            self.logger.error("Error logging round update: %s", e)
            print(f"--- DEBUG: FAILING DATA ---")
            try:
                print(json.dumps(data_to_log, indent=4, default=str))
            except Exception as json_error:
                print(f"Could not serialize data_to_log: {json_error}")
                print(f"Raw data_to_log: {data_to_log}")
            print(f"--- END DEBUG ---")

    def get_round_history(self, shoe_name, limit=50):
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM rounds 
                    WHERE shoe_name = ? 
                    ORDER BY last_updated DESC 
                    LIMIT ?
                """, (shoe_name, limit))
                return cursor.fetchall()

    def get_latest_timestamp(self, shoe_name):
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(last_updated) FROM rounds WHERE shoe_name = ?", (shoe_name,))
                return cursor.fetchone()[0]

    def initialize_shoe_in_db(self, shoe_name, cards):
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO shoe_cards (shoe_name, undealt_cards, dealt_cards)
                    VALUES (?, ?, ?)
                """, (shoe_name, json.dumps(cards), json.dumps([])))
                conn.commit()

    def update_shoe_cards(self, shoe_name, undealt_cards, dealt_cards):
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO shoe_cards (shoe_name, undealt_cards, dealt_cards)
                        VALUES (?, ?, ?)
                        ON CONFLICT(shoe_name) DO UPDATE SET
                            undealt_cards=excluded.undealt_cards,
                            dealt_cards=excluded.dealt_cards
                    """, (shoe_name, json.dumps(undealt_cards), json.dumps(dealt_cards)))
                except Exception:
                    # Fallback for older SQLite without UPSERT
                    cursor.execute(
                        "UPDATE shoe_cards SET undealt_cards = ?, dealt_cards = ? WHERE shoe_name = ?",
                        (json.dumps(undealt_cards), json.dumps(dealt_cards), shoe_name),
                    )
                    if cursor.rowcount == 0:
                        cursor.execute(
                            "INSERT OR REPLACE INTO shoe_cards (shoe_name, undealt_cards, dealt_cards) VALUES (?, ?, ?)",
                            (shoe_name, json.dumps(undealt_cards), json.dumps(dealt_cards)),
                        )
                conn.commit()

    def get_shoe_cards(self, shoe_name):
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT undealt_cards, dealt_cards FROM shoe_cards WHERE shoe_name = ?", (shoe_name,))
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0]), json.loads(result[1])
                return [], []

    def ensure_shoe_cards_columns(self):
        """Ensure extra tracking columns exist on shoe_cards."""
        with self.get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute("PRAGMA table_info('shoe_cards')")
                self.logger.info("Database tables created pragma")
                cols = {row[1] for row in c.fetchall()}
                for col in ["current_dealt_cards", "discarded_cards", "next_shuffling_stack"]:
                    if col not in cols:
                        c.execute(f"ALTER TABLE shoe_cards ADD COLUMN {col} TEXT DEFAULT '[]'")
                conn.commit()
            except Exception as e:
                self.logger.error("ensure_shoe_cards_columns error: %s", e)

    def ensure_shoe_row(self, shoe_name: str):
        """Ensure a row exists in shoe_cards for the given shoe_name."""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT 1 FROM shoe_cards WHERE shoe_name = ?", (shoe_name,))
                if not c.fetchone():
                    c.execute(
                        "INSERT INTO shoe_cards (shoe_name, undealt_cards, dealt_cards, current_dealt_cards, discarded_cards, next_shuffling_stack) "
                        "VALUES (?, '[]', '[]', '[]', '[]', '[]')",
                        (shoe_name,),
                    )
                    conn.commit()
        except Exception as e:
            self.logger.error("ensure_shoe_row error: %s", e)

    def get_last_round_game_id(self, shoe_name: str):
        """Returns the latest game_id by last_updated for a shoe, or None."""
        with self.lock:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT game_id FROM rounds WHERE shoe_name = ? ORDER BY last_updated DESC LIMIT 1",
                    (shoe_name,),
                )
                row = c.fetchone()
                return row[0] if row else None

    def get_round_by_game_id(self, shoe_name: str, game_id: str):
        """Fetch a single round row by game_id and shoe_name."""
        with self.lock:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM rounds WHERE shoe_name = ? AND game_id = ? LIMIT 1",
                    (shoe_name, game_id),
                )
                return c.fetchone()

    def get_shoe_state(self, shoe_name: str):
        """Returns full shoe state arrays from shoe_cards as dict of lists."""
        with self.lock:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """SELECT undealt_cards, dealt_cards, 
                              COALESCE(current_dealt_cards,'[]'), 
                              COALESCE(discarded_cards,'[]'),
                              COALESCE(next_shuffling_stack,'[]')
                       FROM shoe_cards WHERE shoe_name = ?""",
                    (shoe_name,),
                )
                row = c.fetchone()
                if not row:
                    return {"undealt": [], "dealt": [], "current": [], "discarded": [], "next_stack": []}
                j = lambda s: json.loads(s) if s else []
                return {
                    "undealt": j(row[0]),
                    "dealt": j(row[1]),
                    "current": j(row[2]),
                    "discarded": j(row[3]),
                    "next_stack": j(row[4]),
                }

    def update_current_dealt_cards(self, shoe_name: str, cards):
        """Replace current round dealt cards list."""
        self.ensure_shoe_row(shoe_name)
        with self.lock:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE shoe_cards SET current_dealt_cards = ? WHERE shoe_name = ?",
                    (json.dumps(cards), shoe_name),
                )
                conn.commit()

    def append_dealt_cards(self, shoe_name: str, new_cards):
        """Append new_cards to dealt_cards for a shoe."""
        self.ensure_shoe_row(shoe_name)
        with self.lock:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT dealt_cards FROM shoe_cards WHERE shoe_name = ?", (shoe_name,))
                row = c.fetchone()
                prev = json.loads(row[0]) if row and row[0] else []
                prev.extend(new_cards or [])
                c.execute(
                    "UPDATE shoe_cards SET dealt_cards = ? WHERE shoe_name = ?",
                    (json.dumps(prev), shoe_name),
                )
                conn.commit()

    def replace_undealt_cards(self, shoe_name: str, new_undealt):
        """Overwrite undealt_cards for a shoe."""
        self.ensure_shoe_row(shoe_name)
        with self.lock:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE shoe_cards SET undealt_cards = ? WHERE shoe_name = ?",
                    (json.dumps(new_undealt or []), shoe_name),
                )
                conn.commit()

    def append_discarded_cards_left(self, shoe_name: str, cards):
        """Prepend cards to discarded_cards (cards + existing)."""
        with self.lock:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT discarded_cards FROM shoe_cards WHERE shoe_name = ?", (shoe_name,))
                row = c.fetchone()
                prev = json.loads(row[0]) if row and row[0] else []
                newv = list(cards or []) + prev
                c.execute(
                    "UPDATE shoe_cards SET discarded_cards = ? WHERE shoe_name = ?",
                    (json.dumps(newv), shoe_name),
                )
                conn.commit()

    def set_discarded_cards(self, shoe_name: str, cards):
        """Overwrite discarded_cards."""
        with self.lock:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE shoe_cards SET discarded_cards = ? WHERE shoe_name = ?",
                    (json.dumps(cards or []), shoe_name),
                )
                conn.commit()

    def set_next_shuffling_stack(self, shoe_name: str, cards):
        """Set next_shuffling_stack for a shoe."""
        with self.lock:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE shoe_cards SET next_shuffling_stack = ? WHERE shoe_name = ?",
                    (json.dumps(cards or []), shoe_name),
                )
                conn.commit()

    def start_shoe_session(self, shoe_name: str) -> int:
        """Starts a new shoe session and returns the session ID."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shoe_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shoe_name TEXT NOT NULL,
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        final_stats TEXT
                    )
                """)
                cursor.execute("INSERT INTO shoe_sessions (shoe_name,start_time) VALUES (?,?)", (shoe_name, datetime.now()))
                conn.commit()
                return cursor.lastrowid

    def end_shoe_session(self, session_id: int, final_stats: Dict = None):
        """Ends a shoe session with optional final statistics."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                stats_json = json.dumps(final_stats) if final_stats else None
                cursor.execute("""
                    UPDATE shoe_sessions 
                    SET end_time = CURRENT_TIMESTAMP, final_stats = ? 
                    WHERE session_id = ?
                """, (stats_json, session_id))
                conn.commit()

    def save_prediction_validation(self, session_id: int, round_id: int, card_position: int, 
                                 predicted_card: str, actual_card: str, position_offset: int):
        """Saves prediction validation data."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prediction_validation (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        round_id INTEGER,
                        card_position INTEGER,
                        predicted_card TEXT,
                        actual_card TEXT,
                        position_offset INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    INSERT INTO prediction_validation 
                    (session_id, round_id, card_position, predicted_card, actual_card, position_offset)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, round_id, card_position, predicted_card, actual_card, position_offset))
                conn.commit()

    def save_card_tracking(self, session_id: int, round_id: int, card_value: str, 
                          dealt_position: int, seat_number: Optional[int], card_type: str, dealing_order: int):
        """Saves individual card tracking data."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS card_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        round_id INTEGER,
                        card_value TEXT,
                        dealt_position INTEGER,
                        seat_number INTEGER,
                        card_type TEXT,
                        dealing_order INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    INSERT INTO card_tracking 
                    (session_id, round_id, card_value, dealt_position, seat_number, card_type, dealing_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, round_id, card_value, dealt_position, seat_number, card_type, dealing_order))
                conn.commit()

    def update_seat_performance(self, session_id: int, seat_number: int, result: str):
        """Updates seat performance statistics."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS seat_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        seat_number INTEGER,
                        result TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    INSERT INTO seat_performance (session_id, seat_number, result)
                    VALUES (?, ?, ?)
                """, (session_id, seat_number, result))
                conn.commit()

    def get_rounds_since_timestamp(self, shoe_name, timestamp, limit=50):
        """Get rounds that occurred after the specified timestamp."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM rounds 
                    WHERE shoe_name = ? AND last_updated > ? 
                    ORDER BY last_updated ASC 
                    LIMIT ?
                """, (shoe_name, timestamp, limit))
                return cursor.fetchall()
