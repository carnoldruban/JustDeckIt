import sqlite3
import json
import threading
from datetime import datetime
from typing import Dict, Optional
from logging_config import get_logger, log_performance

class DatabaseManager:
    def __init__(self, db_name="blackjack_data.db"):
        self.logger = get_logger("DatabaseManager")
        self.db_name = db_name
        self.lock = threading.Lock()
        self.round_counters = {}  # Track round numbers per shoe
        self.logger.info("Initializing DB: %s", db_name)
        self.create_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    @log_performance
    def create_tables(self):
        self.logger.info("Creating database tables")
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS rounds")
                cursor.execute("DROP TABLE IF EXISTS shoe_cards")
                cursor.execute("DROP TABLE IF EXISTS shoe_sessions")
                cursor.execute("DROP TABLE IF EXISTS prediction_validation")
                cursor.execute("DROP TABLE IF EXISTS card_tracking")
                cursor.execute("DROP TABLE IF EXISTS seat_performance")
                cursor.execute("DROP TABLE IF EXISTS player_hands")
                cursor.execute("DROP TABLE IF EXISTS player_cards")
                cursor.execute("DROP TABLE IF EXISTS player_scores")
                cursor.execute("DROP TABLE IF EXISTS player_states")
                cursor.execute("DROP TABLE IF EXISTS player_actions")
                cursor.execute("DROP TABLE IF EXISTS player_results")
                cursor.execute("DROP TABLE IF EXISTS player_decisions")
                cursor.execute("DROP TABLE IF EXISTS player_counts")

                # Create rounds table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rounds (
                        game_id TEXT,
                        shoe_name TEXT,
                        round_number INTEGER,
                        dealer_hand TEXT,
                        dealer_score TEXT,
                        seat0_hand TEXT, seat0_score TEXT, seat0_state TEXT,
                        seat1_hand TEXT, seat1_score TEXT, seat1_state TEXT,
                        seat2_hand TEXT, seat2_score TEXT, seat2_state TEXT,
                        seat3_hand TEXT, seat3_score TEXT, seat3_state TEXT,
                        seat4_hand TEXT, seat4_score TEXT, seat4_state TEXT,
                        seat5_hand TEXT, seat5_score TEXT, seat5_state TEXT,
                        seat6_hand TEXT, seat6_score TEXT, seat6_state TEXT,
                        last_updated TIMESTAMP,
                        PRIMARY KEY (game_id, last_updated)
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
                        validation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        round_number INTEGER,
                        predicted_cards TEXT,
                        actual_cards TEXT,
                        accuracy REAL,
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
                if shoe_name not in self.round_counters:
                    self.round_counters[shoe_name] = 0
                self.round_counters[shoe_name] += 1
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    data_to_log = {
                        "game_id": game_id,
                        "shoe_name": shoe_name,
                        "round_number": self.round_counters[shoe_name],  # Added
                        "last_updated": datetime.now()
                    }
                    
                    # Extract dealer data
                    if 'dealer' in round_data:
                        dealer = round_data['dealer']
                        data_to_log["dealer_hand"] = json.dumps(dealer.get('cards', []))
                        data_to_log["dealer_score"] = str(dealer.get('score', 0))
                    
                    # Extract seat data
                    if 'seats' in round_data:
                        for seat_num in range(7):
                            seat_key = str(seat_num)
                            if seat_key in round_data['seats']:
                                seat = round_data['seats'][seat_key]
                                if 'first' in seat:
                                    first = seat['first']
                                    data_to_log[f"seat{seat_num}_hand"] = json.dumps(first.get('cards', []))
                                    data_to_log[f"seat{seat_num}_score"] = str(first.get('score', 0))
                                    data_to_log[f"seat{seat_num}_state"] = first.get('state', 'unknown')
                    
                    # Insert into database
                    cursor.execute("""
                        INSERT OR REPLACE INTO rounds (
                            game_id, shoe_name, round_number, last_updated,
                            dealer_hand, dealer_score,
                            seat0_hand, seat0_score, seat0_state,
                            seat1_hand, seat1_score, seat1_state,
                            seat2_hand, seat2_score, seat2_state,
                            seat3_hand, seat3_score, seat3_state,
                            seat4_hand, seat4_score, seat4_state,
                            seat5_hand, seat5_score, seat5_state,
                            seat6_hand, seat6_score, seat6_state
                        ) VALUES (
                            :game_id, :shoe_name, :round_number, :last_updated,
                            :dealer_hand, :dealer_score,
                            :seat0_hand, :seat0_score, :seat0_state,
                            :seat1_hand, :seat1_score, :seat1_state,
                            :seat2_hand, :seat2_score, :seat2_state,
                            :seat3_hand, :seat3_score, :seat3_state,
                            :seat4_hand, :seat4_score, :seat4_state,
                            :seat5_hand, :seat5_score, :seat5_state,
                            :seat6_hand, :seat6_score, :seat6_state
                        )
                    """, data_to_log)
                    
                    conn.commit()
                    self.logger.debug("Logged round update for game %s, round %d", game_id, self.round_counters[shoe_name])
                    
        except Exception as e:
            self.logger.error("Error logging round update: %s", e)

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
                cursor.execute("""
                    UPDATE shoe_cards SET undealt_cards = ?, dealt_cards = ? WHERE shoe_name = ?
                """, (json.dumps(undealt_cards), json.dumps(dealt_cards), shoe_name))
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

    def start_shoe_session(self, shoe_name: str) -> int:
        """Starts a new shoe session and returns the session ID."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS shoe_sessions")
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
                cursor.execute("DROP TABLE IF EXISTS card_tracking")
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
                cursor.execute("DROP TABLE IF EXISTS seat_performance")
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