"""
ULTIMATE LIVE SIMULATION - Complete live blackjack experience
Creates 2 hours of history + live game simulation
"""

import threading
import time
import json
import random
import sqlite3
from datetime import datetime, timedelta
from database_manager import DBManager
from analytics_engine import AnalyticsEngine

class UltimateLiveSimulation:
    def __init__(self):
        self.db_manager = DBManager()
        self.analytics_engine = AnalyticsEngine(self.db_manager)
        
        # Two premium shoes
        self.shoes = ["Premium Shoe 1", "Premium Shoe 2"] 
        self.current_shoe = self.shoes[0]
        self.shoe_index = 0
        
        # Live state
        self.is_running = False
        self.current_round = 0
        self.cards_dealt = 0
        self.session_id = None
        
        print("🎰 Ultimate Live Simulation Ready")

    def setup_complete_environment(self):
        """Create the complete 2-hour + live environment."""
        print("🚀 SETTING UP COMPLETE LIVE ENVIRONMENT")
        print("="*60)
        
        # Step 1: Clear and create historical data
        self.clear_all_data()
        historical_rounds = self.create_historical_data()
        
        # Step 2: Create live tracking status
        self.create_live_tracking_status()
        
        print(f"\n✅ ENVIRONMENT READY!")
        print(f"   📊 Historical: {historical_rounds} rounds over 2 hours")
        print(f"   🎮 Live: Ready to start {self.current_shoe}")
        print(f"   📱 App Status: Ready for tracker_app.py")
        
        return historical_rounds

    def clear_all_data(self):
        """Clear all existing data."""
        if not self.db_manager.conn:
            return
        
        cursor = self.db_manager.conn.cursor()
        tables = ['hand_cards', 'hands', 'game_rounds', 'shoe_sessions', 
                 'seat_performance', 'prediction_validation']
        
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
            except:
                pass
        
        self.db_manager.conn.commit()
        print("🧹 Database cleared")

    def create_historical_data(self):
        """Create 2 hours of realistic historical data."""
        print("📊 Creating 2 hours of historical tracking data...")
        
        start_time = datetime.now() - timedelta(hours=2)
        current_time = start_time
        total_rounds = 0
        session_count = 0
        
        # Create alternating shoe sessions
        while current_time < datetime.now() - timedelta(minutes=10):
            shoe_name = self.shoes[session_count % 2]
            
            # Session duration 20-35 minutes
            duration = random.randint(20, 35)
            remaining = (datetime.now() - timedelta(minutes=10) - current_time).total_seconds() / 60
            duration = min(duration, int(remaining))
            
            if duration < 15:
                break
            
            rounds = int((duration / 60) * 25)  # 25 rounds/hour
            session_rounds = self.create_shoe_session(shoe_name, current_time, rounds)
            
            total_rounds += session_rounds
            session_count += 1
            
            # Different performance for each shoe
            win_rate = 0.62 if "Shoe 1" in shoe_name else 0.44
            print(f"  ✅ {shoe_name}: {session_rounds} rounds, {win_rate:.1%} win rate")
            
            current_time += timedelta(minutes=duration + random.randint(3, 8))
        
        print(f"📈 Historical data complete: {total_rounds} rounds across {session_count} sessions")
        return total_rounds

    def create_shoe_session(self, shoe_name, start_time, num_rounds):
        """Create a complete shoe session."""
        # Start session tracking
        session_id = self.analytics_engine.start_session_tracking(shoe_name)
        
        # Shoe characteristics
        if "Shoe 1" in shoe_name:
            base_win_rate = 0.62  # Hot shoe
            hot_seats = [2, 3, 4]
        else:
            base_win_rate = 0.44  # Cold shoe  
            hot_seats = [1, 5]
        
        session_stats = {'wins': 0, 'losses': 0, 'pushes': 0, 'cards': 0}
        
        for round_num in range(num_rounds):
            game_id = f"HIST_{shoe_name.replace(' ', '')}_{session_id}_{round_num}"
            round_time = start_time + timedelta(minutes=round_num * 2.4)
            
            # Create round with realistic patterns
            round_data = self.create_historical_round(hot_seats, base_win_rate)
            self.save_historical_round(game_id, round_data, round_time)
            
            # Update session stats
            for seat_num, hand in round_data['hands'].items():
                result = hand['result']
                self.analytics_engine.update_seat_performance(seat_num, result)
                
                if result == 'win':
                    session_stats['wins'] += 1
                elif result == 'loss':
                    session_stats['losses'] += 1
                else:
                    session_stats['pushes'] += 1
                
                session_stats['cards'] += len(hand['cards'])
            
            session_stats['cards'] += len(round_data['dealer_cards'])
        
        # End session
        total_hands = session_stats['wins'] + session_stats['losses']
        win_rate = session_stats['wins'] / max(1, total_hands)
        
        self.analytics_engine.end_session_tracking({
            'total_rounds': num_rounds,
            'total_cards_dealt': session_stats['cards'],
            'win_rate': win_rate,
            'dealer_wins': session_stats['losses'],
            'player_wins': session_stats['wins'],
            'pushes': session_stats['pushes']
        })
        
        return num_rounds

    def create_historical_round(self, hot_seats, base_win_rate):
        """Create a single historical round."""
        # Active players (3-5)
        all_seats = [1, 2, 3, 4, 5]
        active_seats = random.sample(all_seats, random.randint(3, 5))
        
        round_data = {
            'dealer_cards': [self.random_card(), self.random_card()],
            'dealer_score': random.randint(17, 21),
            'hands': {}
        }
        
        # Maybe dealer hits
        if random.random() < 0.25:
            round_data['dealer_cards'].append(self.random_card())
            round_data['dealer_score'] = random.randint(17, 26)
        
        # Player hands
        for seat in active_seats:
            # Seat-specific win rate
            win_rate = base_win_rate + (0.06 if seat in hot_seats else -0.04)
            
            # Determine outcome
            if random.random() < win_rate:
                result = 'win'
                score = random.choice([19, 20, 21])
            elif random.random() < 0.07:
                result = 'push'
                score = 20
            else:
                result = 'loss'
                score = random.choice([13, 16, 22])
            
            # Generate cards
            cards = [self.random_card(), self.random_card()]
            if random.random() < 0.3:  # Hit rate
                cards.append(self.random_card())
            
            round_data['hands'][seat] = {
                'cards': cards,
                'score': score,
                'result': result
            }
        
        return round_data

    def random_card(self):
        """Generate random card."""
        values = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
        suits = ['H','D','C','S']
        return random.choice(values) + random.choice(suits)

    def save_historical_round(self, game_id, round_data, timestamp):
        """Save round to database."""
        cursor = self.db_manager.conn.cursor()
        
        # Game round
        cursor.execute(
            "INSERT INTO game_rounds (game_id_str, timestamp) VALUES (?, ?)",
            (game_id, timestamp.isoformat())
        )
        
        # Get round ID
        cursor.execute("SELECT id FROM game_rounds WHERE game_id_str = ?", (game_id,))
        round_id = cursor.fetchone()[0]
        
        # Dealer hand
        cursor.execute(
            "INSERT INTO hands (round_id, seat_num, final_score, result) VALUES (?, ?, ?, ?)",
            (round_id, -1, round_data['dealer_score'], 'stand')
        )
        dealer_hand_id = cursor.lastrowid
        
        for card in round_data['dealer_cards']:
            cursor.execute(
                "INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                (dealer_hand_id, card)
            )
        
        # Player hands
        for seat, hand in round_data['hands'].items():
            cursor.execute(
                "INSERT INTO hands (round_id, seat_num, final_score, result) VALUES (?, ?, ?, ?)",
                (round_id, seat, hand['score'], hand['result'])
            )
            hand_id = cursor.lastrowid
            
            for card in hand['cards']:
                cursor.execute(
                    "INSERT INTO hand_cards (hand_id, card_value) VALUES (?, ?)",
                    (hand_id, card)
                )
        
        self.db_manager.conn.commit()

    def create_live_tracking_status(self):
        """Create files to simulate live tracking."""
        
        # Current game status
        status = {
            'tracking_active': True,
            'current_shoe': self.current_shoe,
            'game_url': 'https://casino.premium.com/blackjack',
            'connection_status': 'CONNECTED',
            'last_update': datetime.now().isoformat(),
            'session_active': True,
            'rounds_this_session': 0,
            'cards_this_session': 0
        }
        
        with open('live_tracking_status.json', 'w') as f:
            json.dump(status, f, indent=2)
        
        # Environment summary
        summary = {
            'environment_ready': True,
            'historical_sessions_loaded': True,
            'live_simulation_ready': True,
            'shoes_available': self.shoes,
            'current_active_shoe': self.current_shoe,
            'analytics_enabled': True,
            'recommendations_active': True
        }
        
        with open('environment_status.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("📱 Live tracking status files created")

    def start_live_dealing(self):
        """Start the live card dealing simulation."""
        print(f"\n🎮 STARTING LIVE SIMULATION")
        print(f"Current Shoe: {self.current_shoe}")
        print("="*50)
        
        # Start live session
        self.session_id = self.analytics_engine.start_session_tracking(self.current_shoe)
        self.is_running = True
        self.current_round = 0
        self.cards_dealt = 0
        
        # Start dealing thread
        deal_thread = threading.Thread(target=self.deal_live_rounds, daemon=True)
        deal_thread.start()
        
        print("🔄 Live dealing started!")
        print("💡 Launch tracker_app.py to see real-time updates")

    def deal_live_rounds(self):
        """Deal live rounds continuously."""
        try:
            while self.is_running:
                self.current_round += 1
                print(f"\n🎲 LIVE Round {self.current_round} - {self.current_shoe}")
                
                # Deal complete round
                self.deal_single_round()
                
                # Check for shoe change (every ~50 rounds)
                if self.current_round % 50 == 0:
                    self.change_shoe()
                
                # Wait between rounds (5 seconds)
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Live dealing error: {e}")

    def deal_single_round(self):
        """Deal a single live round."""
        active_players = random.sample([1,2,3,4,5], random.randint(3,5))
        
        # Deal cards with delays
        for seat in sorted(active_players):
            card = self.random_card()
            self.deal_card_live(seat, card, "First card")
            time.sleep(2)
        
        # Dealer up card
        dealer_card = self.random_card()
        self.deal_card_live(-1, dealer_card, "Dealer up")
        time.sleep(2)
        
        # Second cards
        for seat in sorted(active_players):
            card = self.random_card()
            self.deal_card_live(seat, card, "Second card")
            time.sleep(2)
        
        # Dealer hole
        dealer_hole = self.random_card()
        self.deal_card_live(-1, dealer_hole, "Dealer hole")
        time.sleep(2)
        
        # Some players hit
        for seat in active_players:
            if random.random() < 0.3:
                hit_card = self.random_card()
                self.deal_card_live(seat, hit_card, "Hit")
                time.sleep(2)
        
        print(f"   🏁 Round {self.current_round} complete")

    def deal_card_live(self, seat, card, action):
        """Deal single card with live updates."""
        self.cards_dealt += 1
        
        # Console output
        seat_name = "Dealer" if seat == -1 else f"Seat {seat}"
        print(f"   🃏 {card} → {seat_name} ({action})")
        
        # Update live feed file
        live_card = {
            'card': card,
            'seat': seat,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'round': self.current_round,
            'shoe': self.current_shoe
        }
        
        # Save to live feed
        try:
            try:
                with open('live_card_feed.json', 'r') as f:
                    feed = json.load(f)
            except:
                feed = {'cards': [], 'status': 'active'}
            
            feed['cards'].append(live_card)
            feed['last_update'] = datetime.now().isoformat()
            feed['current_round'] = self.current_round
            feed['current_shoe'] = self.current_shoe
            
            # Keep last 15 cards
            if len(feed['cards']) > 15:
                feed['cards'] = feed['cards'][-15:]
            
            with open('live_card_feed.json', 'w') as f:
                json.dump(feed, f, indent=2)
        except:
            pass

    def change_shoe(self):
        """Change to next shoe."""
        # End current session
        if self.session_id:
            self.analytics_engine.end_session_tracking({
                'total_rounds': 50,
                'total_cards_dealt': self.cards_dealt,
                'win_rate': 0.55 if "Shoe 1" in self.current_shoe else 0.45,
                'dealer_wins': 20,
                'player_wins': 25,
                'pushes': 5
            })
        
        # Switch shoe
        self.shoe_index = (self.shoe_index + 1) % 2
        self.current_shoe = self.shoes[self.shoe_index]
        self.cards_dealt = 0
        
        print(f"\n🔄 SHOE CHANGE: Now using {self.current_shoe}")
        
        # Start new session
        self.session_id = self.analytics_engine.start_session_tracking(self.current_shoe)

    def stop_simulation(self):
        """Stop the live simulation."""
        self.is_running = False
        if self.session_id:
            self.analytics_engine.end_session_tracking({
                'total_rounds': self.current_round,
                'total_cards_dealt': self.cards_dealt,
                'win_rate': 0.50,
                'dealer_wins': 0,
                'player_wins': 0,
                'pushes': 0
            })
        print("🛑 Live simulation stopped")

def main():
    """Run the ultimate simulation."""
    print("🎰 ULTIMATE LIVE BLACKJACK SIMULATION")
    print("="*60)
    print("Creates complete live casino experience:")
    print("• 2 hours of historical tracking data")  
    print("• Live game in progress")
    print("• Real-time card dealing")
    print("• Premium Shoe 1 vs Premium Shoe 2")
    print("="*60)
    
    sim = UltimateLiveSimulation()
    
    try:
        # Setup complete environment
        rounds = sim.setup_complete_environment()
        
        print(f"\n🎯 READY TO START!")
        print(f"Historical data: {rounds} rounds loaded")
        print(f"Live shoe ready: {sim.current_shoe}")
        
        choice = input("\nStart live simulation? (y/n): ").strip().lower()
        
        if choice in ['y', 'yes']:
            sim.start_live_dealing()
            
            print(f"\n🔄 LIVE SIMULATION RUNNING!")
            print("💡 Launch tracker_app.py NOW to see:")
            print("   • Historical 2-hour data in Analytics tab")
            print("   • Live cards being dealt in real-time")
            print("   • Performance comparisons between shoes")
            print("   • Real-time recommendations")
            print("\nPress Ctrl+C to stop simulation...")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                sim.stop_simulation()
        else:
            print("📊 Historical data ready - launch tracker_app.py to explore!")
            
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sim.db_manager.close()

if __name__ == "__main__":
    main()
