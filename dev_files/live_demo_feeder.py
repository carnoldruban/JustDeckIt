"""
Live Demo Card Feeder - Simulates live cards being dealt 
while the tracker app is running to demonstrate real-time features.
"""

import json
import time
import random
import threading
from datetime import datetime, timedelta
from database_manager import DBManager
from analytics_engine import AnalyticsEngine
from prediction_validator import PredictionValidator
import uuid

class LiveDemoFeeder:
    def __init__(self):
        self.db_manager = DBManager()
        self.analytics_engine = AnalyticsEngine(self.db_manager)
        self.prediction_validator = PredictionValidator(self.analytics_engine)
        
        self.card_values = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        self.suits = ['H', 'D', 'C', 'S']
        
        self.is_running = False
        self.current_round = 0
        self.cards_in_round = 0
        self.demo_speed = 3  # seconds between cards
        
        print("🎮 Live Demo Feeder initialized")

    def generate_demo_card(self):
        """Generate a card with some pattern for demo effect."""
        return random.choice(self.card_values) + random.choice(self.suits)

    def create_live_round_demo(self):
        """Create a live round demonstration."""
        self.current_round += 1
        self.cards_in_round = 0
        
        # Start new round
        game_id = f"DEMO_ROUND_{self.current_round}_{int(time.time())}"
        
        print(f"\n🎲 DEMO Round {self.current_round} - Game ID: {game_id}")
        
        # Simulate dealing sequence: Seats 6,5,4,3,2,1,0, then Dealer
        active_seats = random.sample([0,1,2,3,4,5,6], random.randint(3,5))
        active_seats.sort(reverse=True)  # Deal from 6 to 0
        
        round_data = {
            'game_id': game_id,
            'timestamp': datetime.now(),
            'active_seats': active_seats,
            'cards_dealt': [],
            'status': 'in_progress'
        }
        
        # Start prediction for this round
        remaining_cards = [self.generate_demo_card() for _ in range(200)]  # Simulate remaining shoe
        self.prediction_validator.start_round_prediction(remaining_cards)
        
        return round_data

    def deal_card_to_position(self, round_data, seat_num, is_dealer=False):
        """Deal a card to a specific position and update analytics."""
        card = self.generate_demo_card()
        dealing_position = len(round_data['cards_dealt']) + 1
        
        # Add to round data
        card_info = {
            'card': card,
            'seat': seat_num if not is_dealer else -1,
            'position': dealing_position,
            'timestamp': datetime.now(),
            'is_dealer': is_dealer
        }
        round_data['cards_dealt'].append(card_info)
        
        # Update analytics in real-time
        card_type = 'dealer_card' if is_dealer else 'player_card'
        self.analytics_engine.track_card_dealt(
            self.current_round, card, dealing_position, 
            seat_num if not is_dealer else -1, card_type, dealing_position
        )
        
        # Add to prediction validation
        self.prediction_validator.add_dealt_card(card, dealing_position, seat_num if not is_dealer else -1)
        
        # Display real-time info
        position_text = f"Dealer" if is_dealer else f"Seat {seat_num}"
        print(f"   🃏 {card} → {position_text} (Position {dealing_position})")
        
        # Save to live demo file for GUI to read
        self.save_live_card_data(card_info)
        
        return card_info

    def save_live_card_data(self, card_info):
        """Save current card to file for GUI to read in real-time."""
        try:
            # Load existing live data
            try:
                with open('live_demo_feed.json', 'r') as f:
                    live_data = json.load(f)
            except FileNotFoundError:
                live_data = {
                    'current_round': self.current_round,
                    'cards_dealt': [],
                    'last_update': None,
                    'status': 'active'
                }
            
            # Add new card
            live_data['cards_dealt'].append({
                'card': card_info['card'],
                'seat': card_info['seat'],
                'position': card_info['position'],
                'timestamp': card_info['timestamp'].isoformat(),
                'is_dealer': card_info['is_dealer'],
                'round': self.current_round
            })
            
            live_data['last_update'] = datetime.now().isoformat()
            live_data['current_round'] = self.current_round
            
            # Keep only last 20 cards for performance
            if len(live_data['cards_dealt']) > 20:
                live_data['cards_dealt'] = live_data['cards_dealt'][-20:]
            
            # Save updated data
            with open('live_demo_feed.json', 'w') as f:
                json.dump(live_data, f, indent=2)
                
        except Exception as e:
            print(f"   ⚠️ Could not save live data: {e}")

    def complete_round_demo(self, round_data):
        """Complete the round and save to database."""
        
        # Simulate final outcomes
        dealer_score = random.randint(17, 26)
        dealer_result = 'stand' if dealer_score <= 21 else 'bust'
        
        print(f"   🏁 Round {self.current_round} complete - Dealer: {dealer_score} ({dealer_result})")
        
        # Create outcomes for each seat
        outcomes = {}
        for seat_num in round_data['active_seats']:
            # Simulate realistic outcome
            outcome_roll = random.random()
            if outcome_roll < 0.48:  # Player win
                result = 'win'
                score = random.choice([19, 20, 21])
            elif outcome_roll < 0.56:  # Push
                result = 'push'
                score = dealer_score if dealer_score <= 21 else 20
            else:  # Player loss
                result = 'loss'
                score = random.choice([12, 15, 16, 22, 24])
            
            outcomes[seat_num] = {'result': result, 'score': score}
            
            # Update seat performance
            self.analytics_engine.update_seat_performance(seat_num, result)
            
            print(f"      Seat {seat_num}: {score} ({result})")
        
        # End prediction round
        self.prediction_validator.end_round_analysis()
        
        # Save complete round to database
        self.save_complete_round(round_data, outcomes, dealer_score, dealer_result)
        
        return outcomes

    def save_complete_round(self, round_data, outcomes, dealer_score, dealer_result):
        """Save the completed round to the database."""
        if not self.db_manager.conn:
            return
        
        cursor = self.db_manager.conn.cursor()
        
        # Insert game round
        cursor.execute(
            "INSERT INTO game_rounds (game_id_str, timestamp) VALUES (?, ?)",
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
            (round_id, -1, dealer_score, dealer_result)
        )
        dealer_hand_id = cursor.lastrowid
        
        # Add dealer cards
        dealer_cards = [card['card'] for card in round_data['cards_dealt'] if card['is_dealer']]
        for card in dealer_cards:
            cursor.execute(
                "INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                (dealer_hand_id, card)
            )
        
        # Insert player hands
        for seat_num in round_data['active_seats']:
            outcome = outcomes[seat_num]
            cursor.execute(
                "INSERT INTO hands (round_id, seat_num, final_score, result) VALUES (?, ?, ?, ?)",
                (round_id, seat_num, outcome['score'], outcome['result'])
            )
            player_hand_id = cursor.lastrowid
            
            # Add player cards
            player_cards = [card['card'] for card in round_data['cards_dealt'] 
                          if not card['is_dealer'] and card['seat'] == seat_num]
            for card in player_cards:
                cursor.execute(
                    "INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                    (player_hand_id, card)
                )
        
        self.db_manager.conn.commit()

    def run_continuous_demo(self, rounds_to_play=10):
        """Run continuous demo with multiple rounds."""
        print(f"\n🚀 Starting Live Demo - {rounds_to_play} rounds")
        print("="*50)
        
        self.is_running = True
        
        try:
            for round_num in range(rounds_to_play):
                if not self.is_running:
                    break
                
                # Create new round
                round_data = self.create_live_round_demo()
                
                # Deal cards to each active seat (2 cards each)
                for deal_phase in range(2):  # Two dealing phases
                    for seat_num in round_data['active_seats']:
                        if not self.is_running:
                            break
                        
                        self.deal_card_to_position(round_data, seat_num)
                        time.sleep(self.demo_speed)  # Pause between cards
                
                # Deal dealer cards
                if self.is_running:
                    self.deal_card_to_position(round_data, None, is_dealer=True)  # Dealer up card
                    time.sleep(self.demo_speed)
                    
                    self.deal_card_to_position(round_data, None, is_dealer=True)  # Dealer hole card
                    time.sleep(self.demo_speed)
                
                # Sometimes dealer hits
                if self.is_running and random.random() < 0.3:
                    self.deal_card_to_position(round_data, None, is_dealer=True)  # Dealer hit
                    time.sleep(self.demo_speed)
                
                # Complete round
                if self.is_running:
                    outcomes = self.complete_round_demo(round_data)
                    
                    # Show analytics update
                    self.display_live_analytics()
                    
                    # Pause between rounds
                    print(f"\n   ⏳ Next round in {self.demo_speed * 2} seconds...\n")
                    time.sleep(self.demo_speed * 2)
        
        except KeyboardInterrupt:
            print("\n🛑 Demo stopped by user")
        finally:
            self.is_running = False
            self.cleanup_demo()

    def display_live_analytics(self):
        """Display live analytics during demo."""
        try:
            # Get current recommendations
            recommendations = self.analytics_engine.get_decision_recommendations()
            
            # Get prediction accuracy
            accuracy_stats = self.prediction_validator.get_prediction_accuracy_stats()
            
            print(f"   📊 LIVE ANALYTICS:")
            print(f"      Should Play: {'YES ✅' if recommendations.get('should_play') else 'NO ❌'}")
            print(f"      Best Seat: {recommendations.get('best_seat', 'N/A')}")
            print(f"      Prediction Accuracy: {accuracy_stats.get('accuracy', 0):.1%}")
            print(f"      Confidence: {recommendations.get('confidence_level', 'unknown')}")
            
        except Exception as e:
            print(f"   ⚠️ Analytics error: {e}")

    def cleanup_demo(self):
        """Clean up demo resources."""
        try:
            # Create final status file
            final_status = {
                'demo_completed': True,
                'total_rounds': self.current_round,
                'completion_time': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            with open('demo_final_status.json', 'w') as f:
                json.dump(final_status, f, indent=2)
                
            print("🏁 Demo completed and saved")
            
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
        finally:
            if self.db_manager:
                self.db_manager.close()

    def stop_demo(self):
        """Stop the running demo."""
        self.is_running = False

def main():
    """Main demo function - can be run in background while app is open."""
    print("🎮 Live Demo Card Feeder")
    print("This simulates live cards being dealt while the tracker app is running")
    print("="*60)
    
    feeder = LiveDemoFeeder()
    
    try:
        # Check if user wants quick demo or extended
        print("Select demo mode:")
        print("1. Quick Demo (5 rounds, 2 sec intervals)")
        print("2. Realistic Demo (10 rounds, 3 sec intervals)")
        print("3. Extended Demo (20 rounds, 4 sec intervals)")
        
        choice = input("Enter choice (1-3) or press Enter for Quick Demo: ").strip()
        
        if choice == "2":
            feeder.demo_speed = 3
            rounds = 10
        elif choice == "3":
            feeder.demo_speed = 4
            rounds = 20
        else:
            feeder.demo_speed = 2
            rounds = 5
        
        print(f"\n🚀 Starting {rounds} round demo...")
        print("💡 TIP: Open tracker_app.py in another terminal to see live updates!")
        print("Press Ctrl+C to stop demo early\n")
        
        feeder.run_continuous_demo(rounds)
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
