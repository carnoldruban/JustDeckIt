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

        # Table for shoe sessions and tracking
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shoe_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shoe_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_rounds INTEGER DEFAULT 0,
            total_cards_dealt INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            dealer_wins INTEGER DEFAULT 0,
            player_wins INTEGER DEFAULT 0,
            pushes INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        );
        """)

        # Table for seat performance statistics
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS seat_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shoe_session_id INTEGER NOT NULL,
            seat_number INTEGER NOT NULL,
            rounds_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            pushes INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            total_cards_received INTEGER DEFAULT 0,
            FOREIGN KEY (shoe_session_id) REFERENCES shoe_sessions (id)
        );
        """)

        # Table for prediction validation
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_validation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shoe_session_id INTEGER NOT NULL,
            round_id INTEGER NOT NULL,
            card_position INTEGER NOT NULL,
            predicted_card TEXT,
            actual_card TEXT NOT NULL,
            prediction_correct BOOLEAN DEFAULT FALSE,
            position_offset INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (shoe_session_id) REFERENCES shoe_sessions (id),
            FOREIGN KEY (round_id) REFERENCES game_rounds (id)
        );
        """)

        # Table for pattern learning
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shuffle_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shoe_session_id INTEGER NOT NULL,
            pattern_type TEXT NOT NULL,
            pattern_data TEXT NOT NULL,
            accuracy_score REAL DEFAULT 0.0,
            usage_count INTEGER DEFAULT 0,
            last_updated TEXT NOT NULL,
            FOREIGN KEY (shoe_session_id) REFERENCES shoe_sessions (id)
        );
        """)

        # Table for detailed card tracking
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shoe_session_id INTEGER NOT NULL,
            round_id INTEGER NOT NULL,
            card_value TEXT NOT NULL,
            dealt_position INTEGER NOT NULL,
            seat_number INTEGER,
            card_type TEXT,
            dealing_order INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (shoe_session_id) REFERENCES shoe_sessions (id),
            FOREIGN KEY (round_id) REFERENCES game_rounds (id)
        );
        """)

        # Table for analytics summary
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            total_shoes_tracked INTEGER DEFAULT 0,
            best_performing_shoe TEXT,
            worst_performing_shoe TEXT,
            overall_win_rate REAL DEFAULT 0.0,
            best_seat_number INTEGER,
            total_hours_tracked REAL DEFAULT 0.0,
            prediction_accuracy REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );
        """)

        self.conn.commit()
        print("Enhanced database schema created successfully with analytics tables.")

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

    def start_shoe_session(self, shoe_name):
        """Starts a new shoe tracking session."""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO shoe_sessions (shoe_name, start_time, status) 
            VALUES (?, ?, 'active')
        """, (shoe_name, timestamp))
        
        session_id = cursor.lastrowid
        self.conn.commit()
        print(f"Started new shoe session for {shoe_name} with ID {session_id}")
        return session_id

    def end_shoe_session(self, session_id, final_stats=None):
        """Ends a shoe tracking session and updates final statistics."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        
        if final_stats:
            cursor.execute("""
                UPDATE shoe_sessions 
                SET end_time = ?, total_rounds = ?, total_cards_dealt = ?, 
                    win_rate = ?, dealer_wins = ?, player_wins = ?, pushes = ?, status = 'completed'
                WHERE id = ?
            """, (timestamp, final_stats.get('total_rounds', 0), 
                  final_stats.get('total_cards_dealt', 0), final_stats.get('win_rate', 0.0),
                  final_stats.get('dealer_wins', 0), final_stats.get('player_wins', 0),
                  final_stats.get('pushes', 0), session_id))
        else:
            cursor.execute("""
                UPDATE shoe_sessions SET end_time = ?, status = 'completed' WHERE id = ?
            """, (timestamp, session_id))
        
        self.conn.commit()
        print(f"Ended shoe session {session_id}")

    def save_prediction_validation(self, session_id, round_id, card_position, predicted_card, actual_card, position_offset=0):
        """Saves prediction validation data for pattern learning."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        prediction_correct = predicted_card == actual_card
        
        cursor.execute("""
            INSERT INTO prediction_validation 
            (shoe_session_id, round_id, card_position, predicted_card, actual_card, 
             prediction_correct, position_offset, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, round_id, card_position, predicted_card, actual_card, 
              prediction_correct, position_offset, timestamp))
        
        self.conn.commit()

    def save_card_tracking(self, session_id, round_id, card_value, dealt_position, seat_number, card_type, dealing_order):
        """Saves detailed card tracking information."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO card_tracking 
            (shoe_session_id, round_id, card_value, dealt_position, seat_number, card_type, dealing_order, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, round_id, card_value, dealt_position, seat_number, card_type, dealing_order, timestamp))
        
        self.conn.commit()

    def update_seat_performance(self, session_id, seat_number, result):
        """Updates seat performance statistics."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        
        # Check if seat performance record exists
        cursor.execute("""
            SELECT id, rounds_played, wins, losses, pushes, total_cards_received 
            FROM seat_performance 
            WHERE shoe_session_id = ? AND seat_number = ?
        """, (session_id, seat_number))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            seat_id, rounds, wins, losses, pushes, cards = existing
            rounds += 1
            cards += 2  # Assuming 2 cards per hand initially
            
            if result == 'win':
                wins += 1
            elif result == 'loss':
                losses += 1
            elif result == 'push':
                pushes += 1
            
            win_rate = wins / rounds if rounds > 0 else 0.0
            
            cursor.execute("""
                UPDATE seat_performance 
                SET rounds_played = ?, wins = ?, losses = ?, pushes = ?, 
                    win_rate = ?, total_cards_received = ?
                WHERE id = ?
            """, (rounds, wins, losses, pushes, win_rate, cards, seat_id))
        else:
            # Create new record
            rounds = 1
            wins = 1 if result == 'win' else 0
            losses = 1 if result == 'loss' else 0
            pushes = 1 if result == 'push' else 0
            win_rate = wins / rounds if rounds > 0 else 0.0
            cards = 2
            
            cursor.execute("""
                INSERT INTO seat_performance 
                (shoe_session_id, seat_number, rounds_played, wins, losses, pushes, win_rate, total_cards_received)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, seat_number, rounds, wins, losses, pushes, win_rate, cards))
        
        self.conn.commit()

    def get_shoe_performance_stats(self, session_id):
        """Gets comprehensive shoe performance statistics."""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        
        # Get shoe session info
        cursor.execute("SELECT * FROM shoe_sessions WHERE id = ?", (session_id,))
        shoe_info = cursor.fetchone()
        
        # Get seat performance
        cursor.execute("SELECT * FROM seat_performance WHERE shoe_session_id = ?", (session_id,))
        seat_stats = cursor.fetchall()
        
        # Get prediction accuracy
        cursor.execute("""
            SELECT 
                COUNT(*) as total_predictions,
                SUM(CASE WHEN prediction_correct = 1 THEN 1 ELSE 0 END) as correct_predictions
            FROM prediction_validation WHERE shoe_session_id = ?
        """, (session_id,))
        prediction_stats = cursor.fetchone()
        
        return {
            'shoe_info': shoe_info,
            'seat_stats': seat_stats,
            'prediction_stats': prediction_stats
        }

    def get_analytics_summary(self, date_filter=None):
        """Gets comprehensive analytics summary for decision making."""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        
        # Base query for analytics
        base_query = """
            SELECT 
                ss.shoe_name,
                ss.win_rate,
                ss.total_rounds,
                ss.dealer_wins,
                ss.player_wins,
                AVG(sp.win_rate) as avg_seat_win_rate,
                COUNT(DISTINCT sp.seat_number) as active_seats
            FROM shoe_sessions ss
            LEFT JOIN seat_performance sp ON ss.id = sp.shoe_session_id
        """
        
        if date_filter:
            base_query += " WHERE ss.start_time >= ?"
            cursor.execute(base_query + " GROUP BY ss.id", (date_filter,))
        else:
            cursor.execute(base_query + " GROUP BY ss.id")
        
        results = cursor.fetchall()
        
        return {
            'shoe_performances': results,
            'generated_at': datetime.now().isoformat()
        }


    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    db = DBManager()
    # The tables are created on initialization now.
    db.close()
