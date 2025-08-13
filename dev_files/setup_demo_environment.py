"""
Setup Demo Environment - Creates 2 hours of realistic tracking data 
and prepares the app for live demonstration of enhanced features.
"""

import sqlite3
import random
import json
from datetime import datetime, timedelta
from database_manager import DBManager
from analytics_engine import AnalyticsEngine
from prediction_validator import PredictionValidator
import uuid

class DemoEnvironmentSetup:
    def __init__(self):
        self.db_manager = DBManager()
        self.analytics_engine = AnalyticsEngine(self.db_manager)
        self.prediction_validator = PredictionValidator(self.analytics_engine)
        
        # Demo parameters for realistic 2-hour session
        self.shoes = ["Lucky Shoe A", "Hot Shoe B", "Cold Shoe C", "Shoe D"]
        self.seats = [0, 1, 2, 3, 4, 5, 6]
        self.card_values = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        self.suits = ['H', 'D', 'C', 'S']
        
        # Create realistic patterns for demo
        self.winning_patterns = {
            "Lucky Shoe A": {"base_win_rate": 0.58, "best_seats": [2, 3, 4]},
            "Hot Shoe B": {"base_win_rate": 0.55, "best_seats": [1, 2, 5]},
            "Cold Shoe C": {"base_win_rate": 0.42, "best_seats": [0, 6]},
            "Shoe D": {"base_win_rate": 0.47, "best_seats": [3, 4]}
        }
        
        print("🎯 Demo Environment Setup initialized")

    def clear_existing_data(self):
        """Clear existing data to start fresh."""
        if not self.db_manager.conn:
            return
        
        cursor = self.db_manager.conn.cursor()
        
        # Clear all data
        tables_to_clear = [
            'hand_cards', 'hands', 'game_rounds',
            'shoe_sessions', 'seat_performance', 'prediction_validation',
            'shuffle_patterns', 'card_tracking', 'analytics_summary'
        ]
        
        for table in tables_to_clear:
            try:
                cursor.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                pass  # Table might not exist yet
        
        self.db_manager.conn.commit()
        print("🧹 Cleared existing data")

    def generate_realistic_card(self):
        """Generate a card with some realistic distribution."""
        return random.choice(self.card_values) + random.choice(self.suits)

    def create_demo_round(self, game_id, shoe_name, round_num, timestamp):
        """Create a realistic round with patterns that show the benefits."""
        patterns = self.winning_patterns[shoe_name]
        
        # Select 3-6 active seats
        num_active = random.randint(3, 6)
        active_seats = random.sample(self.seats, num_active)
        
        # Create round data
        round_data = {
            'game_id': game_id,
            'shoe_name': shoe_name,
            'timestamp': timestamp,
            'dealer_cards': [],
            'dealer_score': 0,
            'dealer_result': 'stand',
            'hands': {}
        }
        
        # Generate dealer hand
        dealer_cards = [self.generate_realistic_card(), self.generate_realistic_card()]
        dealer_score = random.randint(17, 21)
        
        # Sometimes dealer busts or hits
        if random.random() < 0.25:  # 25% chance dealer hits
            dealer_cards.append(self.generate_realistic_card())
            dealer_score = random.randint(19, 26)  # May bust
        
        round_data['dealer_cards'] = dealer_cards
        round_data['dealer_score'] = dealer_score
        
        # Generate player hands with realistic patterns
        for seat_num in active_seats:
            # Apply shoe-specific patterns
            base_win_rate = patterns['base_win_rate']
            
            # Best seats get bonus
            if seat_num in patterns['best_seats']:
                win_rate = min(0.65, base_win_rate + 0.08)
            else:
                win_rate = max(0.35, base_win_rate - 0.05)
            
            # Determine outcome
            outcome_roll = random.random()
            if outcome_roll < win_rate:
                outcome = 'win'
                score = random.choice([19, 20, 21])
            elif outcome_roll < win_rate + 0.08:  # Push rate
                outcome = 'push'
                score = dealer_score if dealer_score <= 21 else 20
            else:
                outcome = 'loss'
                score = random.choice([12, 13, 14, 15, 16, 22, 23, 24])
            
            # Generate cards
            player_cards = [self.generate_realistic_card(), self.generate_realistic_card()]
            
            # Add third card sometimes
            if random.random() < 0.35:
                player_cards.append(self.generate_realistic_card())
            
            round_data['hands'][seat_num] = {
                'cards': player_cards,
                'score': score,
                'result': outcome
            }
        
        return round_data

    def save_round_to_database(self, round_data):
        """Save round to database using existing structure."""
        if not self.db_manager.conn:
            return
        
        cursor = self.db_manager.conn.cursor()
        
        # Insert game round
        cursor.execute(
            "INSERT OR IGNORE INTO game_rounds (game_id_str, timestamp) VALUES (?, ?)",
            (round_data['game_id'], round_data['timestamp'].isoformat())
        )
        
        # Get round ID
        cursor.execute("SELECT id FROM game_rounds WHERE game_id_str = ?", (round_data['game_id'],))
        round_row = cursor.fetchone()
        if not round_row:
            return
        round_id = round_row[0]
        
        # Insert dealer hand
        cursor.execute(
            "INSERT INTO hands (round_id, seat_num, final_score, result) VALUES (?, ?, ?, ?)",
            (round_id, -1, round_data['dealer_score'], round_data['dealer_result'])
        )
        dealer_hand_id = cursor.lastrowid
        
        for card in round_data['dealer_cards']:
            cursor.execute(
                "INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                (dealer_hand_id, card)
            )
        
        # Insert player hands
        for seat_num, hand_data in round_data['hands'].items():
            cursor.execute(
                "INSERT INTO hands (round_id, seat_num, final_score, result) VALUES (?, ?, ?, ?)",
                (round_id, seat_num, hand_data['score'], hand_data['result'])
            )
            player_hand_id = cursor.lastrowid
            
            for card in hand_data['cards']:
                cursor.execute(
                    "INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                    (player_hand_id, card)
                )
        
        self.db_manager.conn.commit()

    def create_shoe_session(self, shoe_name, start_time, duration_minutes):
        """Create a complete shoe session with realistic data."""
        print(f"🎰 Creating {shoe_name} session ({duration_minutes} min)...")
        
        # Start analytics session
        session_id = self.analytics_engine.start_session_tracking(shoe_name)
        
        # Calculate rounds (30 per hour typical)
        total_rounds = int((duration_minutes / 60) * 30)
        
        session_stats = {
            'total_rounds': 0,
            'dealer_wins': 0,
            'player_wins': 0,
            'pushes': 0,
            'cards_dealt': 0
        }
        
        current_time = start_time
        
        for round_num in range(total_rounds):
            game_id = str(uuid.uuid4())
            round_timestamp = current_time + timedelta(minutes=round_num * 2)  # 2 min per round
            
            # Create and save round
            round_data = self.create_demo_round(game_id, shoe_name, round_num, round_timestamp)
            self.save_round_to_database(round_data)
            
            # Update analytics
            for seat_num, hand_data in round_data['hands'].items():
                result = hand_data['result']
                self.analytics_engine.update_seat_performance(seat_num, result)
                
                # Update session stats
                if result == 'win':
                    session_stats['player_wins'] += 1
                elif result == 'loss':
                    session_stats['dealer_wins'] += 1
                else:
                    session_stats['pushes'] += 1
                
                session_stats['cards_dealt'] += len(hand_data['cards'])
            
            session_stats['cards_dealt'] += len(round_data['dealer_cards'])
            session_stats['total_rounds'] += 1
        
        # End session
        win_rate = session_stats['player_wins'] / max(1, session_stats['player_wins'] + session_stats['dealer_wins'])
        final_stats = {
            'total_rounds': session_stats['total_rounds'],
            'total_cards_dealt': session_stats['cards_dealt'],
            'win_rate': win_rate,
            'dealer_wins': session_stats['dealer_wins'],
            'player_wins': session_stats['player_wins'],
            'pushes': session_stats['pushes']
        }
        
        self.analytics_engine.end_session_tracking(final_stats)
        print(f"  ✅ {shoe_name}: {total_rounds} rounds, {win_rate:.1%} win rate")
        
        return session_id, final_stats

    def setup_two_hour_history(self):
        """Create 2 hours of realistic tracking history."""
        print("🕐 Setting up 2-hour tracking history...")
        
        # Clear existing data
        self.clear_existing_data()
        
        # Start time: 2 hours ago
        start_time = datetime.now() - timedelta(hours=2)
        current_time = start_time
        
        sessions_created = []
        total_rounds = 0
        
        # Create multiple shoe sessions
        shoe_index = 0
        while current_time < datetime.now() - timedelta(minutes=10):  # Leave 10 min for "current" session
            shoe_name = self.shoes[shoe_index % len(self.shoes)]
            
            # Vary session duration (25-45 minutes)
            duration = random.randint(25, 45)
            
            # Don't exceed remaining time
            remaining_minutes = (datetime.now() - timedelta(minutes=10) - current_time).total_seconds() / 60
            duration = min(duration, int(remaining_minutes))
            
            if duration < 15:  # Skip very short sessions
                break
            
            session_id, stats = self.create_shoe_session(shoe_name, current_time, duration)
            
            sessions_created.append({
                'shoe_name': shoe_name,
                'duration': duration,
                'start_time': current_time,
                'stats': stats
            })
            
            total_rounds += stats['total_rounds']
            current_time += timedelta(minutes=duration + random.randint(3, 8))  # Gap between shoes
            shoe_index += 1
        
        print(f"✅ Created {len(sessions_created)} sessions with {total_rounds} rounds")
        return sessions_created

    def create_live_test_data(self):
        """Create test data files for simulating live game input."""
        
        # Create a sequence of incoming cards for demo
        live_cards = []
        for i in range(50):  # 50 cards for demo
            live_cards.append({
                'round': i // 7 + 1,  # ~7 cards per round
                'position': i % 7,
                'card': self.generate_realistic_card(),
                'seat': random.choice([-1, 0, 1, 2, 3, 4, 5, 6]) if i % 7 < 6 else -1,  # Last card is dealer
                'timestamp': (datetime.now() + timedelta(seconds=i * 3)).isoformat()
            })
        
        # Save to JSON file for the demo
        with open('demo_live_cards.json', 'w') as f:
            json.dump(live_cards, f, indent=2)
        
        # Create current shoe status
        current_shoe_data = {
            'name': 'Demo Live Shoe',
            'cards_remaining': random.randint(150, 200),
            'current_count': random.randint(-5, 8),
            'penetration': random.uniform(0.3, 0.7),
            'prediction_confidence': random.uniform(0.6, 0.9)
        }
        
        with open('demo_current_shoe.json', 'w') as f:
            json.dump(current_shoe_data, f, indent=2)
        
        print("📋 Created live test data files")
        return live_cards, current_shoe_data

    def generate_summary_report(self, sessions):
        """Generate a summary of the demo environment."""
        
        total_rounds = sum(s['stats']['total_rounds'] for s in sessions)
        total_cards = sum(s['stats']['total_cards_dealt'] for s in sessions)
        
        # Get analytics
        analysis = self.analytics_engine.get_shoe_performance_analysis(hours_back=3)
        recommendations = self.analytics_engine.get_decision_recommendations()
        
        summary = {
            'environment_ready': True,
            'historical_data': {
                'sessions': len(sessions),
                'total_rounds': total_rounds,
                'total_cards_dealt': total_cards,
                'duration_hours': 2.0
            },
            'analytics_ready': {
                'shoes_analyzed': len(analysis.get('shoe_performance', [])),
                'seats_tracked': len(analysis.get('seat_performance', [])),
                'recommendations_available': bool(recommendations)
            },
            'live_demo_ready': {
                'test_cards_prepared': True,
                'current_shoe_simulated': True,
                'real_time_features_active': True
            },
            'key_insights': {
                'best_shoe': analysis.get('shoe_performance', [{}])[0].get('name', 'N/A') if analysis.get('shoe_performance') else 'N/A',
                'best_seats': [s['seat_number'] for s in analysis.get('seat_performance', [])[:3]],
                'should_play_now': recommendations.get('should_play', False),
                'confidence_level': recommendations.get('confidence_level', 'unknown')
            }
        }
        
        with open('demo_environment_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary

def main():
    """Set up the complete demo environment."""
    print("🚀 Setting up Demo Environment for Enhanced Blackjack Tracker")
    print("="*60)
    
    setup = DemoEnvironmentSetup()
    
    try:
        # Step 1: Create 2-hour historical data
        sessions = setup.setup_two_hour_history()
        
        # Step 2: Create live test data
        live_cards, current_shoe = setup.create_live_test_data()
        
        # Step 3: Generate summary
        summary = setup.generate_summary_report(sessions)
        
        # Final report
        print("\n" + "="*60)
        print("🎉 DEMO ENVIRONMENT READY!")
        print("="*60)
        
        print(f"\n📈 HISTORICAL DATA (2 HOURS):")
        print(f"   • {summary['historical_data']['sessions']} shoe sessions")
        print(f"   • {summary['historical_data']['total_rounds']} rounds played")
        print(f"   • {summary['historical_data']['total_cards_dealt']} cards dealt")
        
        print(f"\n🔬 ANALYTICS READY:")
        print(f"   • {summary['analytics_ready']['shoes_analyzed']} shoes analyzed")
        print(f"   • {summary['analytics_ready']['seats_tracked']} seats tracked")
        print(f"   • Recommendations: {'✅' if summary['analytics_ready']['recommendations_available'] else '❌'}")
        
        print(f"\n🎯 KEY INSIGHTS:")
        print(f"   • Best Shoe: {summary['key_insights']['best_shoe']}")
        print(f"   • Best Seats: {summary['key_insights']['best_seats']}")
        print(f"   • Should Play Now: {'YES' if summary['key_insights']['should_play_now'] else 'NO'}")
        print(f"   • Confidence: {summary['key_insights']['confidence_level']}")
        
        print(f"\n🎮 LIVE DEMO READY:")
        print(f"   • Test cards prepared: ✅")
        print(f"   • Current shoe simulated: ✅")
        print(f"   • Real-time features active: ✅")
        
        print(f"\n🚀 NEXT STEPS:")
        print(f"   1. Run: python tracker_app.py")
        print(f"   2. Go to 'Analytics & Predictions' tab")
        print(f"   3. See 2 hours of data and live insights!")
        print(f"   4. Watch real-time recommendations")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        setup.db_manager.close()

if __name__ == "__main__":
    main()
