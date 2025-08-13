"""
Progressive Blackjack Test Data Generator
Creates realistic progressive dealing like real casino WebSocket messages
"""

import json
import random
import time
from datetime import datetime

class ProgressiveBlackjackGenerator:
    def __init__(self):
        self.current_game_id = None
        self.round_number = 0
        self.suits = ['♠', '♥', '♦', '♣']
        self.ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        self.deck = self._create_deck()
        self.shuffle_deck()
        
    def _create_deck(self):
        """Create a standard 8-deck shoe"""
        deck = []
        for _ in range(8):  # 8 decks
            for suit in self.suits:
                for rank in self.ranks:
                    deck.append({'rank': rank, 'suit': suit})
        return deck
    
    def shuffle_deck(self):
        """Shuffle the deck"""
        random.shuffle(self.deck)
    
    def draw_card(self):
        """Draw a card from the deck"""
        if len(self.deck) < 50:  # Reshuffle when getting low
            self.deck = self._create_deck()
            self.shuffle_deck()
        return self.deck.pop()
    
    def card_to_value_string(self, card):
        """Convert card to the format used in casino logs"""
        return f"{card['rank']}{card['suit']}"
    
    def calculate_hand_score(self, cards):
        """Calculate blackjack hand score"""
        score = 0
        aces = 0
        
        for card in cards:
            rank = card['value'].replace('♠', '').replace('♥', '').replace('♦', '').replace('♣', '')
            if rank in ['J', 'Q', 'K']:
                score += 10
            elif rank == 'A':
                aces += 1
                score += 11
            else:
                score += int(rank)
        
        # Handle aces
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        
        return score
    
    def generate_new_game_id(self):
        """Generate a new game ID"""
        self.round_number += 1
        timestamp = int(time.time() * 1000)
        self.current_game_id = f"sim{timestamp}{random.randint(1000, 9999)}"
        return self.current_game_id
    
    def create_progressive_round(self):
        """Create a progressive round with multiple messages for the same gameId"""
        game_id = self.generate_new_game_id()
        messages = []
        
        # Initialize game state
        dealer_cards = []
        seats = {
            "0": {"first": {"cards": [], "score": 0, "state": "playing"}},
            "1": {"first": {"cards": [], "score": 0, "state": "playing"}},
            "2": {"first": {"cards": [], "score": 0, "state": "playing"}},
        }
        
        # Determine which seats are active this round
        active_seats = random.sample(list(seats.keys()), random.randint(1, 3))
        
        # Message 1: Initial deal - First card to each player
        for seat_num in active_seats:
            card = self.draw_card()
            card_value = self.card_to_value_string(card)
            seats[seat_num]["first"]["cards"].append({"value": card_value})
        
        # Add dealer's first card (face up)
        dealer_card = self.draw_card()
        dealer_cards.append({"value": self.card_to_value_string(dealer_card)})
        
        messages.append(self._create_message(game_id, dealer_cards[:], seats))
        
        # Message 2: Second cards to players and dealer hole card
        for seat_num in active_seats:
            card = self.draw_card()
            card_value = self.card_to_value_string(card)
            seats[seat_num]["first"]["cards"].append({"value": card_value})
            seats[seat_num]["first"]["score"] = self.calculate_hand_score(seats[seat_num]["first"]["cards"])
        
        # Dealer hole card
        dealer_hole = self.draw_card()
        dealer_cards.append({"value": self.card_to_value_string(dealer_hole)})
        
        messages.append(self._create_message(game_id, dealer_cards[:], seats))
        
        # Message 3-N: Player decisions (hit/stand)
        for seat_num in active_seats:
            # Randomly decide if player hits
            while random.random() < 0.4 and seats[seat_num]["first"]["score"] < 21:  # 40% chance to hit
                card = self.draw_card()
                card_value = self.card_to_value_string(card)
                seats[seat_num]["first"]["cards"].append({"value": card_value})
                seats[seat_num]["first"]["score"] = self.calculate_hand_score(seats[seat_num]["first"]["cards"])
                
                # Create message after each hit
                messages.append(self._create_message(game_id, dealer_cards[:], seats))
                
                if seats[seat_num]["first"]["score"] >= 21:
                    break
        
        # Final message: Dealer plays and results
        dealer_score = self.calculate_hand_score(dealer_cards)
        
        # Dealer hits to 17
        while dealer_score < 17:
            card = self.draw_card()
            dealer_cards.append({"value": self.card_to_value_string(card)})
            dealer_score = self.calculate_hand_score(dealer_cards)
        
        # Determine results
        for seat_num in active_seats:
            player_score = seats[seat_num]["first"]["score"]
            if player_score > 21:
                seats[seat_num]["first"]["result"] = "loss"
                seats[seat_num]["first"]["state"] = "busted"
            elif dealer_score > 21:
                seats[seat_num]["first"]["result"] = "win"
                seats[seat_num]["first"]["state"] = "won"
            elif player_score > dealer_score:
                seats[seat_num]["first"]["result"] = "win"
                seats[seat_num]["first"]["state"] = "won"
            elif player_score < dealer_score:
                seats[seat_num]["first"]["result"] = "loss"
                seats[seat_num]["first"]["state"] = "lost"
            else:
                seats[seat_num]["first"]["result"] = "push"
                seats[seat_num]["first"]["state"] = "push"
        
        # Create final message with results
        dealer_data = {
            "cards": dealer_cards,
            "score": dealer_score,
            "result": "dealer_complete"
        }
        
        final_payload = {
            "gameId": game_id,
            "dealer": dealer_data,
            "seats": {k: v for k, v in seats.items() if k in active_seats}
        }
        
        final_message = {
            "serialized_object": json.dumps({"payloadData": final_payload}),
            "timestamp": datetime.now().isoformat(),
            "message_type": "game_complete"
        }
        
        messages.append(final_message)
        
        return messages
    
    def _create_message(self, game_id, dealer_cards, seats):
        """Create a WebSocket message in the expected format"""
        # Remove empty seats for this message
        active_seats = {k: v for k, v in seats.items() if v["first"]["cards"]}
        
        dealer_data = {
            "cards": dealer_cards,
            "score": self.calculate_hand_score(dealer_cards) if len(dealer_cards) > 1 else None
        }
        
        payload = {
            "gameId": game_id,
            "dealer": dealer_data,
            "seats": active_seats
        }
        
        return {
            "serialized_object": json.dumps({"payloadData": payload}),
            "timestamp": datetime.now().isoformat(),
            "message_type": "game_update"
        }
    
    def generate_progressive_test_data(self, num_rounds=50):
        """Generate progressive test data for multiple rounds"""
        all_messages = []
        
        print(f"[PROGRESSIVE GEN] Generating {num_rounds} rounds with progressive dealing...")
        
        for round_num in range(num_rounds):
            round_messages = self.create_progressive_round()
            all_messages.extend(round_messages)
            
            if (round_num + 1) % 10 == 0:
                print(f"[PROGRESSIVE GEN] Generated {round_num + 1} rounds...")
        
        print(f"[PROGRESSIVE GEN] Total messages generated: {len(all_messages)}")
        return all_messages

def main():
    """Generate progressive test data"""
    generator = ProgressiveBlackjackGenerator()
    
    # Generate 50 rounds (will create ~200-300 messages total)
    test_data = generator.generate_progressive_test_data(50)
    
    # Save to file
    filename = "blackjack_progressive_test_data.json"
    with open(filename, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    print(f"[PROGRESSIVE GEN] Successfully generated progressive test data!")
    print(f"[PROGRESSIVE GEN] File: {filename}")
    print(f"[PROGRESSIVE GEN] Total messages: {len(test_data)}")
    print(f"[PROGRESSIVE GEN] Estimated rounds: ~50")
    print(f"[PROGRESSIVE GEN] Average messages per round: {len(test_data) / 50:.1f}")
    
    # Show sample of first few messages
    print(f"\n[PROGRESSIVE GEN] Sample messages:")
    for i, msg in enumerate(test_data[:5]):
        payload = json.loads(msg["serialized_object"])
        game_id = payload["payloadData"]["gameId"]
        dealer_cards = len(payload["payloadData"]["dealer"]["cards"])
        seats_count = len(payload["payloadData"]["seats"])
        print(f"  Message {i+1}: GameID={game_id[-6:]} Dealer={dealer_cards}cards Seats={seats_count}")

if __name__ == "__main__":
    main()
