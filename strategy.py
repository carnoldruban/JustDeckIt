# Card values mapping
card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}

# S17 Basic Strategy Charts (Dealer Stands on Soft 17)
s17_hard_hand_chart = {
    # Player Sum: { Dealer Up-card: Action }
    17: {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 'A':'S'},
    16: {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    15: {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    14: {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    13: {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    12: {2:'H', 3:'H', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    11: {2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'D', 'A':'H'}, # Corrected A vs 11
    10: {2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'H', 'A':'H'},
    9:  {2:'H', 3:'D', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    8:  {2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
}

s17_soft_hand_chart = {
    # Player Sum: { Dealer Up-card: Action }
    20: {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 'A':'S'}, # A,9
    19: {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 'A':'S'}, # A,8
    18: {2:'DS', 3:'DS', 4:'DS', 5:'DS', 6:'DS', 7:'S', 8:'S', 9:'H', 10:'H', 'A':'H'}, # A,7. DS = Double if allowed, else Stand
    17: {2:'H', 3:'D', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'}, # A,6
    16: {2:'H', 3:'H', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'}, # A,5
    15: {2:'H', 3:'H', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'}, # A,4
    14: {2:'H', 3:'H', 4:'H', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'}, # A,3
    13: {2:'H', 3:'H', 4:'H', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'}, # A,2
}

s17_pair_chart = {
    # Player Pair: { Dealer Up-card: Action }
    'A': {2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'P', 9:'P', 10:'P', 'A':'P'},
    'T': {2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 'A':'S'},
    '9': {2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'S', 8:'P', 9:'P', 10:'S', 'A':'S'},
    '8': {2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'P', 9:'P', 10:'P', 'A':'P'},
    '7': {2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 'A':'H'},
    '6': {2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    '5': {2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'H', 'A':'H'},
    '4': {2:'H', 3:'H', 4:'H', 5:'P', 6:'P', 7:'H', 8:'H', 9:'H', 10:'H', 'A':'H'},
    '3': {2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 'A':'H'},
    '2': {2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 'A':'H'},
}

# Hi-Lo Deviations (Illustrious 18 as a base)
s17_deviations = {
    (16, 10): (0, 'S'), (15, 10): (4, 'S'), (13, 2): (-1, 'H'),
    (12, 3): (2, 'S'), (12, 2): (3, 'S'), (11, 'A'): (1, 'D'),
    (10, 'A'): (4, 'D'), (10, 10): (4, 'D'), (9, 2): (1, 'D'),
    (9, 7): (3, 'D'), ('T,T', 5): (5, 'P'), ('T,T', 6): (4, 'P'),
}

def get_hand_value(hand):
    value = sum(card_values[card] for card in hand)
    aces = hand.count('A')
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def get_strategy_action(player_hand, dealer_up_card, true_count):
    player_sum = get_hand_value(player_hand)
    # Dealer up-card value should be rank (first char) from strings like "['TH', '7S']"
    dealer_rank = dealer_up_card[0] if isinstance(dealer_up_card, str) else dealer_up_card
    dealer_val = card_values[dealer_rank]

    is_pair = len(player_hand) == 2 and player_hand[0] == player_hand[1]
    is_soft = 'A' in player_hand and get_hand_value(player_hand) != get_hand_value([c for c in player_hand if c != 'A'] + ['1'])

    # 1. Check for Deviations
    deviation_key = (player_sum, dealer_val)
    if is_pair: deviation_key = (f'{player_hand[0]},{player_hand[1]}', dealer_val)

    if deviation_key in s17_deviations:
        tc_threshold, action = s17_deviations[deviation_key]
        if true_count >= tc_threshold: return action

    # 2. Use Pair chart
    if is_pair: return s17_pair_chart[player_hand[0]][dealer_up_card]

    # 3. Use Soft Hand chart
    if is_soft:
        if player_sum >= 19: return 'S'
        return s17_soft_hand_chart.get(player_sum, {})[dealer_up_card]

    # 4. Use Hard Hand chart
    if player_sum >= 17: return 'S'
    if player_sum <= 8: return 'H'
    return s17_hard_hand_chart.get(player_sum, {})[dealer_up_card]

def get_bet_recommendation(true_count):
    if true_count < 1: return "Wait / Min Bet"
    if true_count < 2: return "Bet 1 Unit"
    if true_count < 3: return "Bet 2 Units"
    if true_count < 4: return "Bet 3 Units"
    return "Bet 4+ Units"
