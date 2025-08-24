# H17 (Dealer Hits on Soft 17) Basic Strategy
# Player hands are rows, Dealer up-cards are columns (2-A)
# H: Hit, S: Stand, D: Double, P: Split

HARD_TOTALS = {
    # 17+ always stand
    17: ['S','S','S','S','S','S','S','S','S','S'],
    16: ['S','S','S','S','S','H','H','H','H','H'],
    15: ['S','S','S','S','S','H','H','H','H','H'],
    14: ['S','S','S','S','S','H','H','H','H','H'],
    13: ['S','S','S','S','S','H','H','H','H','H'],
    12: ['H','H','S','S','S','H','H','H','H','H'],
    11: ['D','D','D','D','D','D','D','D','D','D'],
    10: ['D','D','D','D','D','D','D','D','H','H'],
    9:  ['H','D','D','D','D','H','H','H','H','H'],
    # 8 and below always hit
}

SOFT_TOTALS = {
    # A,9 (20) and A,8 (19) always stand against H17
    19: ['S','D','S','S','S','S','S','S','S','S'], # A,8 vs 6 is Double
    18: ['S','D','D','D','D','S','S','H','H','H'], # A,7
    17: ['H','D','D','D','D','H','H','H','H','H'], # A,6
    16: ['H','H','D','D','D','H','H','H','H','H'], # A,5
    15: ['H','H','H','D','D','H','H','H','H','H'], # A,4
    14: ['H','H','H','D','D','H','H','H','H','H'], # A,3
    13: ['H','H','H','D','D','H','H','H','H','H'], # A,2
}

PAIRS = {
    'A': ['P','P','P','P','P','P','P','P','P','P'],
    'T': ['S','S','S','S','S','S','S','S','S','S'], # 10,J,Q,K
    '9': ['P','P','P','P','P','S','P','P','S','S'],
    '8': ['P','P','P','P','P','P','P','P','P','P'],
    '7': ['P','P','P','P','P','P','H','H','H','H'],
    '6': ['P','P','P','P','P','H','H','H','H','H'],
    '5': ['D','D','D','D','D','D','D','D','H','H'],
    '4': ['H','H','H','P','P','H','H','H','H','H'],
    '3': ['P','P','P','P','P','P','H','H','H','H'],
    '2': ['P','P','P','P','P','P','H','H','H','H'],
}

# Illustrious 18 Deviations from Basic Strategy
DEVIATIONS = {
    "16v10": {"tc": 0, "action": "S"},
    "15v10": {"tc": 4, "action": "S"},
    "10v10": {"tc": 4, "action": "D"}, # T,T vs 10
    "12v3": {"tc": 2, "action": "S"},
    "12v2": {"tc": 3, "action": "S"},
    "11vA": {"tc": 1, "action": "D"},
    "10vA": {"tc": 4, "action": "D"},
    "9v2": {"tc": 1, "action": "D"},
    "9v7": {"tc": 3, "action": "D"},
    "16v9": {"tc": 5, "action": "S"},
    "13v2": {"tc": -1, "action": "H"},
    "12v4": {"tc": 0, "action": "S"},
    "12v5": {"tc": -2, "action": "S"},
    "12v6": {"tc": -1, "action": "S"},
    "13v3": {"tc": -2, "action": "H"},
    "insurance": {"tc": 3, "action": "INSURE"},
}

def _get_hand_value(hand: list[str]) -> (int, bool):
    """Calculates the value of a hand. Returns (value, is_soft)."""
    value = 0
    num_aces = 0
    for card_str in hand:
        rank = card_str[0].upper()
        if rank == 'A':
            num_aces += 1
            value += 11
        elif rank in ['K', 'Q', 'J', 'T']:
            value += 10
        else:
            value += int(rank)

    while value > 21 and num_aces > 0:
        value -= 10
        num_aces -= 1

    is_soft = (num_aces > 0) and (value + 10 <= 21) if value != 11 else (num_aces > 1)
    if value == 11 and num_aces > 0:
        is_soft = True


    return value, is_soft

def get_strategy_action(player_hand: list[str], dealer_up_card: str, true_count: float) -> str:
    """Gets the basic strategy action, applying deviations for H17 rules."""
    player_value, is_soft = _get_hand_value(player_hand)
    dealer_rank = dealer_up_card[0].upper()
    dealer_val_for_col = 11 if dealer_rank == 'A' else 10 if dealer_rank in ['T','J','Q','K'] else int(dealer_rank)
    dealer_col = dealer_val_for_col - 2 if dealer_val_for_col <= 10 else 9 # A is col 9

    # 1. Insurance Deviation
    if dealer_rank == 'A' and true_count >= DEVIATIONS["insurance"]["tc"]:
        return "INSURE"

    # 2. Check for Deviations
    deviation_key = f"{player_value}v{dealer_val_for_col}"
    if deviation_key in DEVIATIONS and true_count >= DEVIATIONS[deviation_key]["tc"]:
        return DEVIATIONS[deviation_key]["action"]

    # 3. Check for Pairs
    if len(player_hand) == 2 and player_hand[0][0] == player_hand[1][0]:
        pair_rank = player_hand[0][0].upper()
        return PAIRS[pair_rank][dealer_col]

    # 4. Check for Soft Totals
    if is_soft:
        if player_value >= 20: return 'S' # A,9 always stands
        if player_value == 19 and dealer_val_for_col != 6: return 'S' # A,8 stands unless vs 6
        return SOFT_TOTALS.get(player_value, 'H')[dealer_col]

    # 5. Check for Hard Totals
    if player_value >= 17: return 'S'
    if player_value <= 8: return 'H'
    return HARD_TOTALS.get(player_value, 'H')[dealer_col]

def get_bet_recommendation(true_count: float) -> dict:
    """Recommends a bet size based on the true count with color coding."""
    if true_count < 1:
        return {"text": "Wait / Min Bet", "color": "red"}
    elif true_count < 2:
        return {"text": "Bet 1 Unit", "color": "#006400"} # DarkGreen
    elif true_count < 3:
        return {"text": "Bet 2 Units", "color": "green"}
    elif true_count < 4:
        return {"text": "Bet 4 Units", "color": "#FFD700"} # Gold
    else:
        return {"text": "Bet 8+ Units", "color": "#FF8C00"} # DarkOrange
