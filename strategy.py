"""
Handles blackjack strategy decisions, including Basic Strategy and deviations.
"""

# Basic Strategy for 6 Decks, Dealer Hits on Soft 17 (H17)
# Actions: S=Stand, H=Hit, D=Double, P=Split

# Player's hard totals (no Ace or Ace counts as 1)
# Key: Player's total, Value: Dict of {Dealer's upcard: Action}
hard_totals_chart = {
    17: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'S', 8: 'S', 9: 'S', 10: 'S', 'A': 'S'},
    16: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    15: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    14: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    13: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    12: {2: 'H', 3: 'H', 4: 'S', 5: 'S', 6: 'S', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    11: {2: 'D', 3: 'D', 4: 'D', 5: 'D', 6: 'D', 7: 'D', 8: 'D', 9: 'D', 10: 'D', 'A': 'D'},
    10: {2: 'D', 3: 'D', 4: 'D', 5: 'D', 6: 'D', 7: 'D', 8: 'D', 9: 'D', 10: 'H', 'A': 'H'},
    9:  {2: 'H', 3: 'D', 4: 'D', 5: 'D', 6: 'D', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    8:  {2: 'H', 3: 'H', 4: 'H', 5: 'H', 6: 'H', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
}

# Player's soft totals (Ace counts as 11)
# Key: Player's non-Ace card total, Value: Dict of {Dealer's upcard: Action}
soft_totals_chart = {
    9: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'S', 8: 'S', 9: 'S', 10: 'S', 'A': 'S'}, # A,9 (20)
    8: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'S', 8: 'S', 9: 'S', 10: 'S', 'A': 'S'}, # A,8 (19)
    7: {2: 'D', 3: 'D', 4: 'D', 5: 'D', 6: 'D', 7: 'S', 8: 'S', 9: 'H', 10: 'H', 'A': 'H'}, # A,7 (18)
    6: {2: 'H', 3: 'D', 4: 'D', 5: 'D', 6: 'D', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'}, # A,6 (17)
    5: {2: 'H', 3: 'H', 4: 'D', 5: 'D', 6: 'D', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'}, # A,5 (16)
    4: {2: 'H', 3: 'H', 4: 'D', 5: 'D', 6: 'D', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'}, # A,4 (15)
    3: {2: 'H', 3: 'H', 4: 'H', 5: 'D', 6: 'D', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'}, # A,3 (14)
    2: {2: 'H', 3: 'H', 4: 'H', 5: 'D', 6: 'D', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'}, # A,2 (13)
}

# Player's pairs
# Key: Player's pair card value, Value: Dict of {Dealer's upcard: Action}
pairs_chart = {
    'A': {2: 'P', 3: 'P', 4: 'P', 5: 'P', 6: 'P', 7: 'P', 8: 'P', 9: 'P', 10: 'P', 'A': 'P'},
    10: {2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'S', 8: 'S', 9: 'S', 10: 'S', 'A': 'S'}, # 10,J,Q,K
    9:  {2: 'P', 3: 'P', 4: 'P', 5: 'P', 6: 'P', 7: 'S', 8: 'P', 9: 'P', 10: 'S', 'A': 'S'},
    8:  {2: 'P', 3: 'P', 4: 'P', 5: 'P', 6: 'P', 7: 'P', 8: 'P', 9: 'P', 10: 'P', 'A': 'P'},
    7:  {2: 'P', 3: 'P', 4: 'P', 5: 'P', 6: 'P', 7: 'P', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    6:  {2: 'P', 3: 'P', 4: 'P', 5: 'P', 6: 'P', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    5:  {2: 'D', 3: 'D', 4: 'D', 5: 'D', 6: 'D', 7: 'D', 8: 'D', 9: 'D', 10: 'H', 'A': 'H'},
    4:  {2: 'H', 3: 'H', 4: 'H', 5: 'P', 6: 'P', 7: 'H', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    3:  {2: 'P', 3: 'P', 4: 'P', 5: 'P', 6: 'P', 7: 'P', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
    2:  {2: 'P', 3: 'P', 4: 'P', 5: 'P', 6: 'P', 7: 'P', 8: 'H', 9: 'H', 10: 'H', 'A': 'H'},
}

def _get_card_value(card):
    """Converts a card string to a numerical value. 'A' is always 11 here."""
    if card in ['J', 'Q', 'K', '10']:
        return 10
    if card == 'A':
        return 11
    return int(card)

def get_hand_value(hand):
    """
    Calculates the total value of a hand, handling Aces correctly.
    Returns a tuple: (total, is_soft)
    """
    hard_total = sum(_get_card_value(c) for c in hand if c != 'A')
    num_aces = hand.count('A')

    if num_aces == 0:
        return hard_total, False

    # Check if one ace can be 11 without busting
    if hard_total + 11 + (num_aces - 1) <= 21:
        total = hard_total + 11 + (num_aces - 1)
        is_soft = True
    else:
        total = hard_total + num_aces
        is_soft = False

    return total, is_soft

# -- Hi-Lo Count Deviations --
# Based on the "Illustrious 18". Structure:
# {
#   "player_total": The player's hand total.
#   "dealer_card": The dealer's up-card.
#   "threshold": The true count threshold to trigger the deviation.
#   "comparison": "ge" (>=) or "le" (<=).
#   "action": The action to take ('S' for Stand, 'H' for Hit, etc.).
#   "is_soft": (optional) True if the player total is soft.
#   "is_pair": (optional) True if the hand is a pair.
# }
deviations = [
    # Insurance
    {"player_total": "any", "dealer_card": "A", "threshold": 3, "comparison": "ge", "action": "Insurance"},

    # Hard Totals (must not be a pair)
    {"player_total": 16, "is_pair": False, "dealer_card": 10, "threshold": 0, "comparison": "ge", "action": "S"},
    {"player_total": 15, "is_pair": False, "dealer_card": 10, "threshold": 4, "comparison": "ge", "action": "S"},
    {"player_total": 13, "is_pair": False, "dealer_card": 2, "threshold": -1, "comparison": "le", "action": "H"},
    {"player_total": 13, "is_pair": False, "dealer_card": 3, "threshold": -2, "comparison": "le", "action": "H"},
    {"player_total": 12, "is_pair": False, "dealer_card": 2, "threshold": 3, "comparison": "ge", "action": "S"},
    {"player_total": 12, "is_pair": False, "dealer_card": 3, "threshold": 2, "comparison": "ge", "action": "S"},
    {"player_total": 12, "is_pair": False, "dealer_card": 4, "threshold": 0, "comparison": "le", "action": "H"},
    {"player_total": 11, "is_pair": False, "dealer_card": "A", "threshold": 1, "comparison": "ge", "action": "D"},
    {"player_total": 10, "is_pair": False, "dealer_card": "A", "threshold": 4, "comparison": "ge", "action": "D"},
    {"player_total": 10, "is_pair": False, "dealer_card": 10, "threshold": 4, "comparison": "ge", "action": "D"},
    {"player_total": 9, "is_pair": False, "dealer_card": 2, "threshold": 1, "comparison": "ge", "action": "D"},
    {"player_total": 9, "is_pair": False, "dealer_card": 7, "threshold": 3, "comparison": "ge", "action": "D"},

    # Pairs
    {"player_total": 20, "is_pair": True, "dealer_card": 5, "threshold": 5, "comparison": "ge", "action": "P"},
    {"player_total": 20, "is_pair": True, "dealer_card": 6, "threshold": 4, "comparison": "ge", "action": "P"},
]


def get_strategy_action(player_hand, dealer_up_card, true_count=0):
    """
    Determines the correct strategy action, including Hi-Lo deviations.
    - player_hand: A list of cards (e.g., ['A', '6'])
    - dealer_up_card: A single card (e.g., '7')
    - true_count: The current true count for deviation calculations.
    """
    dealer_lookup_val = 'A' if dealer_up_card == 'A' else _get_card_value(dealer_up_card)
    total, is_soft = get_hand_value(player_hand)
    is_pair = len(player_hand) == 2 and player_hand[0] == player_hand[1]

    # 1. Check for Deviations
    for dev in deviations:
        match = False
        # Check player total
        if dev["player_total"] == "any" or dev["player_total"] == total:
            # Check dealer card
            if dev["dealer_card"] == dealer_lookup_val:
                # Check soft/pair conditions
                dev_is_soft = dev.get("is_soft", False)
                dev_is_pair = dev.get("is_pair", False)

                # Check if the hand type (soft, pair, hard) matches the deviation rule.
                if dev_is_soft == is_soft and dev_is_pair == is_pair:
                    # Check threshold
                    if dev["comparison"] == "ge" and true_count >= dev["threshold"]:
                        match = True
                    elif dev["comparison"] == "le" and true_count <= dev["threshold"]:
                        match = True

        if match:
            return dev["action"]

    # 2. Basic Strategy: Check for pairs (only on two-card hands)
    if is_pair:
        card = player_hand[0]
        pair_lookup_val = 'A' if card == 'A' else _get_card_value(card)
        if pair_lookup_val in pairs_chart:
            action = pairs_chart[pair_lookup_val][dealer_lookup_val]
            if action != 'D': # Defer 5,5 to hard 10 logic
                return action

    # 3. Basic Strategy: Check for soft totals
    if is_soft:
        non_ace_total = total - 11
        if non_ace_total in soft_totals_chart:
            return soft_totals_chart[non_ace_total][dealer_lookup_val]

    # 4. Basic Strategy: Handle hard totals
    if total >= 17: return 'S'
    if total <= 8: return 'H'
    if total in hard_totals_chart:
        return hard_totals_chart[total][dealer_lookup_val]

    return 'H' # Default action


def get_bet_recommendation(true_count):
    """
    Recommends a bet size in units based on the true count.
    This is a sample betting ramp.
    """
    if true_count <= 1:
        return 1  # Table minimum
    elif true_count <= 2:
        return 2
    elif true_count <= 3:
        return 4
    elif true_count <= 4:
        return 6
    else:  # true_count > 4
        return 8
