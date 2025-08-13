#!/usr/bin/env python3
"""
Generate 3 hours of casino data in exact format for testing
Creates a JSON file with 180 rounds (3 hours) of realistic blackjack data
"""

import json
import random
from datetime import datetime, timedelta

def calculate_hand_value(cards):
    """Calculate blackjack hand value"""
    value = 0
    aces = 0
    
    for card in cards:
        if card in ['J', 'Q', 'K']:
            value += 10
        elif card == 'A':
            aces += 1
            value += 11
        else:
            value += int(card)
    
    # Adjust for aces
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    
    return value

def generate_realistic_hand(target_outcome, is_dealer=False):
    """Generate realistic cards for target outcome"""
    cards = []
    
    if target_outcome == "Win":
        # Player wins - give player strong hand
        if is_dealer:
            # Dealer busts or has weak hand
            cards = [random.choice(['6', '7', '8']), random.choice(['10', 'J', 'Q', 'K'])]
            total = calculate_hand_value(cards)
            if total < 17:  # Dealer must hit
                cards.append(random.choice(['8', '9', '10', 'J']))
        else:
            # Player gets good hand
            cards = [random.choice(['10', 'J', 'Q', 'K']), random.choice(['A', '9', '10'])]
    
    elif target_outcome == "Loss":
        # Player loses
        if is_dealer:
            # Dealer gets strong hand
            cards = [random.choice(['9', '10', 'J']), random.choice(['8', '9', '10'])]
        else:
            # Player busts or has weak hand
            cards = [random.choice(['10', 'J', 'Q']), random.choice(['6', '7', '8'])]
            if calculate_hand_value(cards) < 17:
                cards.append(random.choice(['8', '9', '10']))
    
    else:  # Push
        target_value = random.choice([17, 18, 19, 20])
        if is_dealer:
            cards = ['10', '7'] if target_value == 17 else ['10', '8']
        else:
            cards = ['9', '8'] if target_value == 17 else ['10', '8']
    
    return cards

def create_casino_payload(round_num, shoe_name, timestamp, game_id):
    """Create exact casino payload format"""
    
    # Different win rates for shoes
    if shoe_name == "Shoe 1":
        win_probability = 0.62  # Hot shoe
    else:  # Shoe 2
        win_probability = 0.44  # Cold shoe
    
    # Determine outcome
    rand = random.random()
    if rand < win_probability:
        outcome = "Win"
        payout = 100
    elif rand < win_probability + 0.05:  # 5% pushes
        outcome = "Push"
        payout = 0
    else:
        outcome = "Loss"
        payout = -100
    
    # Generate realistic cards
    player_cards = generate_realistic_hand(outcome, is_dealer=False)
    dealer_cards = generate_realistic_hand(outcome, is_dealer=True)
    
    # Calculate totals
    player_total = calculate_hand_value(player_cards)
    dealer_total = calculate_hand_value(dealer_cards)
    
    # Create payload in EXACT casino format
    payload = {
        "gameId": game_id,
        "tableId": f"table_{shoe_name.lower().replace(' ', '_')}",
        "roundNumber": round_num,
        "timestamp": timestamp.isoformat(),
        "gameState": "completed",
        "dealer": {
            "cards": [{"value": card, "suit": random.choice(["hearts", "diamonds", "clubs", "spades"])} 
                     for card in dealer_cards],
            "total": dealer_total
        },
        "seats": {
            "1": {
                "first": {
                    "cards": [{"value": card, "suit": random.choice(["hearts", "diamonds", "clubs", "spades"])} 
                             for card in player_cards],
                    "total": player_total,
                    "outcome": outcome,
                    "bet": 100,
                    "payout": payout
                }
            }
        },
        "payloadData": {
            "round": round_num,
            "shoe": shoe_name,
            "status": "active"
        }
    }
    
    return payload

def generate_3hour_data():
    """Generate 3 hours of casino data"""
    print("🎰 GENERATING 3 HOURS OF CASINO DATA...")
    print("=" * 50)
    
    all_rounds = []
    start_time = datetime.now() - timedelta(hours=3)
    
    round_num = 1
    game_id_base = 5000
    
    # 3 hours = 180 rounds (1 round per minute average)
    total_rounds = 180
    
    for i in range(total_rounds):
        # Switch shoes every 45 rounds (every 45 minutes)
        if i < 45:
            shoe = "Shoe 1"
        elif i < 90:
            shoe = "Shoe 2"
        elif i < 135:
            shoe = "Shoe 1"
        else:
            shoe = "Shoe 2"
        
        # Create timestamp (1 minute per round)
        round_time = start_time + timedelta(minutes=i)
        game_id = f"game_{game_id_base + i}"
        
        # Create payload
        payload = create_casino_payload(round_num, shoe, round_time, game_id)
        all_rounds.append(payload)
        
        round_num += 1
        
        # Progress updates
        if (i + 1) % 30 == 0:
            hours_progress = (i + 1) / 60
            print(f"   ✅ Generated {i + 1} rounds ({hours_progress:.1f} hours) - Current: {shoe}")
    
    # Save to JSON file
    filename = "3hour_casino_data.json"
    with open(filename, 'w') as f:
        json.dump(all_rounds, f, indent=2)
    
    print(f"\n✅ COMPLETE! Generated {total_rounds} rounds")
    print(f"📁 Saved to: {filename}")
    print(f"📊 Data breakdown:")
    
    # Show statistics
    shoe1_rounds = [r for r in all_rounds if r['payloadData']['shoe'] == 'Shoe 1']
    shoe2_rounds = [r for r in all_rounds if r['payloadData']['shoe'] == 'Shoe 2']
    
    shoe1_wins = len([r for r in shoe1_rounds if r['seats']['1']['first']['outcome'] == 'Win'])
    shoe2_wins = len([r for r in shoe2_rounds if r['seats']['1']['first']['outcome'] == 'Win'])
    
    print(f"   🎰 Shoe 1: {len(shoe1_rounds)} rounds, {shoe1_wins} wins ({shoe1_wins/len(shoe1_rounds)*100:.1f}%)")
    print(f"   🎰 Shoe 2: {len(shoe2_rounds)} rounds, {shoe2_wins} wins ({shoe2_wins/len(shoe2_rounds)*100:.1f}%)")
    print(f"   ⏰ Time span: 3 hours")
    print(f"   📈 Ready for fast forward (2hr) + real-time (1hr) testing")
    
    return filename, all_rounds

if __name__ == "__main__":
    filename, data = generate_3hour_data()
    
    print(f"\n🧪 SAMPLE PAYLOAD:")
    print(json.dumps(data[0], indent=2))
