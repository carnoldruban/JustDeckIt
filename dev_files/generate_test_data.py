"""
Test Data Generator for Blackjack Simulation
Generates 300 rounds of realistic blackjack game data based on the console log format
"""

import json
import random
import time
from datetime import datetime, timedelta

class BlackjackTestDataGenerator:
    def __init__(self):
        # Card deck setup
        self.suits = ['H', 'D', 'C', 'S']  # Hearts, Diamonds, Clubs, Spades
        self.values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        
        # Player names pool
        self.player_names = [
            "NWL", "kingtut987", "virtuxl", "BlackjackPro", "CardShark", "Lucky7",
            "PokerFace", "HighRoller", "AceHunter", "VegasVibes", "ChipLeader",
            "CardMaster", "BluffKing", "WinnerCircle", "AllInAce", "RoyalFlush"
        ]
        
        # Seat configuration (seats 0-6)
        self.available_seats = [0, 1, 2, 3, 4, 5, 6]
        
        # Running timestamp for realistic progression
        self.current_timestamp = time.time()
        
    def generate_card(self):
        """Generate a random card value like '7H', 'KS', 'AD', etc."""
        return f"{random.choice(self.values)}{random.choice(self.suits)}"
        
    def calculate_hand_value(self, cards):
        """Calculate blackjack hand value"""
        value = 0
        aces = 0
        
        for card in cards:
            card_val = card['value'][:-1]  # Remove suit
            if card_val in ['J', 'Q', 'K']:
                value += 10
            elif card_val == 'A':
                aces += 1
                value += 11
            else:
                value += int(card_val)
        
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
            
        return value
        
    def generate_hand_result(self, player_score, dealer_score):
        """Determine hand result based on scores"""
        if player_score > 21:
            return "loss"
        elif dealer_score > 21:
            return "win"
        elif player_score == dealer_score:
            return "push"
        elif player_score > dealer_score:
            return "win"
        else:
            return "loss"
            
    def generate_chips_data(self, seats_playing):
        """Generate realistic betting chips data"""
        chips = {}
        for seat in seats_playing:
            # Main bet: 5-50 range, mostly 10-20
            main_bet = random.choices([5, 10, 12, 15, 20, 25, 30, 50], 
                                    weights=[5, 20, 15, 15, 20, 10, 10, 5])[0]
            
            seat_chips = [{
                "type": "bj-main",
                "amount": main_bet,
                "commission": main_bet * 0.1
            }]
            
            # Side bets (30% chance)
            if random.random() < 0.3:
                if random.random() < 0.5:  # Perfect pair bet
                    pp_bet = random.choice([1, 2, 3, 5])
                    seat_chips.append({
                        "type": "bj-sidebet-perfectpair",
                        "amount": pp_bet
                    })
                    
                if random.random() < 0.4:  # 21+3 bet
                    bet_21_3 = random.choice([1, 2, 3, 5])
                    seat_chips.append({
                        "type": "bj-sidebet-21-3",
                        "amount": bet_21_3
                    })
            
            chips[str(seat)] = seat_chips
            
        return chips
        
    def generate_seats_data(self, active_seats):
        """Generate player seat information"""
        seats_data = {}
        
        for seat in active_seats:
            player_id = f"player_{random.randint(100000, 999999)}"
            player_name = random.choice(self.player_names)
            
            seats_data[str(seat)] = {
                "playerId": player_id,
                "playerName": player_name,
                "hotness": random.randint(0, 3),
                "earlyCashout": random.choice([True, False]),
                "buyTo18": False,
                "allowDoingBetBehindOnMe": True
            }
            
        return seats_data
        
    def generate_single_round(self, round_num):
        """Generate a single complete blackjack round"""
        
        # Generate unique game ID
        game_id = f"sim{int(self.current_timestamp)}{random.randint(1000, 9999)}"
        
        # Determine active seats (2-5 players typically)
        num_players = random.choices([2, 3, 4, 5], weights=[20, 40, 30, 10])[0]
        active_seats = random.sample(self.available_seats, num_players)
        active_seats.sort()
        
        # Generate dealer hand
        dealer_cards = []
        # First card (visible)
        dealer_cards.append({
            "value": self.generate_card(),
            "deck": -1,
            "t": int(self.current_timestamp * 1000)
        })
        
        # Second card (hidden during play, revealed at end)
        dealer_cards.append({
            "value": self.generate_card(),
            "deck": -1, 
            "t": int(self.current_timestamp * 1000) + 1000
        })
        
        # Calculate dealer final score
        dealer_score = self.calculate_hand_value(dealer_cards)
        
        # If dealer has soft 17, hit
        if dealer_score == 17:
            # Check if it's soft 17
            has_ace = any('A' in card['value'] for card in dealer_cards)
            if has_ace and random.random() < 0.6:  # Dealer hits soft 17 60% of time
                dealer_cards.append({
                    "value": self.generate_card(),
                    "deck": -1,
                    "t": int(self.current_timestamp * 1000) + 2000
                })
                dealer_score = self.calculate_hand_value(dealer_cards)
        
        # Generate player hands
        seats = {}
        for seat in active_seats:
            # Generate player hand
            player_cards = []
            player_cards.append({
                "value": self.generate_card(),
                "deck": -1,
                "t": int(self.current_timestamp * 1000) + 500
            })
            player_cards.append({
                "value": self.generate_card(), 
                "deck": -1,
                "t": int(self.current_timestamp * 1000) + 1500
            })
            
            player_score = self.calculate_hand_value(player_cards)
            
            # Player decision logic (simplified)
            state = "InitialDecision"
            if player_score == 21:
                state = "Finished"
            elif player_score < 12:
                # Hit once more
                player_cards.append({
                    "value": self.generate_card(),
                    "deck": -1,
                    "t": int(self.current_timestamp * 1000) + 2500
                })
                player_score = self.calculate_hand_value(player_cards)
                state = "Finished" if player_score >= 17 else "InitialDecision"
                
            # Determine result
            result = self.generate_hand_result(player_score, dealer_score)
            
            seats[str(seat)] = {
                "first": {
                    "cards": player_cards,
                    "score": player_score,
                    "state": state,
                    "result": result
                }
            }
        
        # Generate chips data
        chips_data = self.generate_chips_data(active_seats)
        
        # Generate seats info
        seats_info = self.generate_seats_data(active_seats)
        
        # Create complete game payload
        payload = {
            "gameId": game_id,
            "dealer": {
                "cards": dealer_cards,
                "score": dealer_score
            },
            "seats": seats,
            "chips": chips_data,
            "dealingOrder": [],
            "dealingSequence": [],
            "eventTime": datetime.fromtimestamp(self.current_timestamp).strftime("%H:%M:%S.%f")[:-3],
            "localTime": datetime.fromtimestamp(self.current_timestamp).strftime("%H:%M:%S.%f")[:-3],
            "latency": random.randint(-2, 1),
            "videoTime": datetime.fromtimestamp(self.current_timestamp - 2).strftime("%H:%M:%S.%f")[:-3],
            "videoDelay": random.randint(2000, 3000)
        }
        
        # Advance timestamp for next round (30-120 seconds between rounds)
        self.current_timestamp += random.randint(30, 120)
        
        return {
            "timestamp": self.current_timestamp,
            "event_type": "log",
            "log_args": [None],
            "serialized_object": json.dumps({"payloadData": payload})
        }
        
    def generate_test_data(self, num_rounds=300):
        """Generate complete test data file with specified number of rounds"""
        print(f"[DATA GEN] Generating {num_rounds} rounds of blackjack test data...")
        
        all_rounds = []
        
        for i in range(num_rounds):
            round_data = self.generate_single_round(i + 1)
            all_rounds.append(round_data)
            
            if (i + 1) % 50 == 0:
                print(f"[DATA GEN] Generated {i + 1} rounds...")
        
        # Save to file
        output_file = "blackjack_test_data_300rounds.json"
        with open(output_file, 'w') as f:
            json.dump(all_rounds, f, indent=2)
            
        print(f"[DATA GEN] Successfully generated {num_rounds} rounds!")
        print(f"[DATA GEN] Data saved to: {output_file}")
        print(f"[DATA GEN] File size: {len(json.dumps(all_rounds)) / 1024:.1f} KB")
        
        return output_file

if __name__ == "__main__":
    generator = BlackjackTestDataGenerator()
    generator.generate_test_data(300)
