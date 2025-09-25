import sqlite3
import json
import os
from contextlib import contextmanager
from typing import List, Tuple, Optional, Dict, Any

from logging_config import get_logger, log_performance

logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            data_dir = 'data'
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, 'blackjack_tracker.db')

        self.create_tables()

    @contextmanager
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @log_performance
    def create_tables(self):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Main table for round data
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_rounds (
                game_id TEXT PRIMARY KEY,
                shoe_name TEXT,
                round_number INTEGER,
                dealer_hand TEXT,
                dealer_score INTEGER,
                seat0_hand TEXT, seat0_score INTEGER, seat0_state TEXT,
                seat1_hand TEXT, seat1_score INTEGER, seat1_state TEXT,
                seat2_hand TEXT, seat2_score INTEGER, seat2_state TEXT,
                seat3_hand TEXT, seat3_score INTEGER, seat3_state TEXT,
                seat4_hand TEXT, seat4_score INTEGER, seat4_state TEXT,
                seat5_hand TEXT, seat5_score INTEGER, seat5_state TEXT,
                seat6_hand TEXT, seat6_score INTEGER, seat6_state TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Table for shoe card states
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS shoe_cards (
                shoe_name TEXT PRIMARY KEY,
                undealt_cards TEXT,
                dealt_cards TEXT,
                discarded_cards TEXT,
                current_cards TEXT,
                next_shuffling_stack TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()

    @log_performance
    def save_round(self, round_data: Dict[str, Any]):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            query = """
            INSERT OR REPLACE INTO game_rounds (
                game_id, shoe_name, round_number, dealer_hand, dealer_score,
                seat0_hand, seat0_score, seat0_state,
                seat1_hand, seat1_score, seat1_state,
                seat2_hand, seat2_score, seat2_state,
                seat3_hand, seat3_score, seat3_state,
                seat4_hand, seat4_score, seat4_state,
                seat5_hand, seat5_score, seat5_state,
                seat6_hand, seat6_score, seat6_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            values = [
                round_data.get('game_id'),
                round_data.get('shoe_name'),
                round_data.get('round_number'),
                json.dumps(round_data.get('dealer', {}).get('hand')),
                round_data.get('dealer', {}).get('score'),
            ]

            for i in range(7):
                seat = round_data.get(f'seat{i}', {})
                values.extend([
                    json.dumps(seat.get('hand')),
                    seat.get('score'),
                    seat.get('state')
                ])

            cursor.execute(query, values)
            conn.commit()

    @log_performance
    def get_round_history(self, shoe_name: str, limit: int = 10) -> List[Tuple]:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM game_rounds
            WHERE shoe_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """, (shoe_name, limit))
            return cursor.fetchall()

    @log_performance
    def get_latest_timestamp(self, shoe_name: str) -> Optional[str]:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(timestamp) FROM game_rounds WHERE shoe_name = ?", (shoe_name,))
            result = cursor.fetchone()
            return result[0] if result else None

    @log_performance
    def get_rounds_since_timestamp(self, shoe_name: str, timestamp: str) -> List[Tuple]:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM game_rounds
            WHERE shoe_name = ? AND timestamp > ?
            ORDER BY timestamp ASC
            """, (shoe_name, timestamp))
            return cursor.fetchall()

    @log_performance
    def save_shoe_state(self, shoe_name: str, state: Dict[str, Any]):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            query = """
            INSERT OR REPLACE INTO shoe_cards (
                shoe_name, undealt_cards, dealt_cards, discarded_cards, current_cards, next_shuffling_stack, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

            values = [
                shoe_name,
                json.dumps(state.get("undealt", [])),
                json.dumps(state.get("dealt", [])),
                json.dumps(state.get("discarded", [])),
                json.dumps(state.get("current", [])),
                json.dumps(state.get("next_shuffling_stack", [])),
            ]

            cursor.execute(query, values)
            conn.commit()

    @log_performance
    def get_shoe_state(self, shoe_name: str) -> Dict[str, Any]:
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shoe_cards WHERE shoe_name = ?", (shoe_name,))
            row = cursor.fetchone()

            if not row:
                return {}

            return {
                "shoe_name": row[0],
                "undealt": json.loads(row[1] or '[]'),
                "dealt": json.loads(row[2] or '[]'),
                "discarded": json.loads(row[3] or '[]'),
                "current": json.loads(row[4] or '[]'),
                "next_shuffling_stack": json.loads(row[5] or '[]'),
                "last_updated": row[6]
            }

    @log_oog_performance
    def get_shoe_cards(self, shoe_name: str) -> Tuple[List[str], List[str]]:
        state = self.get_shoe_state(shoe_name)
        return state.get("undealt", []), state.get("dealt", [])

    @log_performance
    def get_discarded_cards(self, shoe_name: str) -> List[str]:
        state = self.get_shoe_state(shoe_name)
        return state.get("discarded", [])