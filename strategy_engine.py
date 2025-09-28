"""
Blackjack Strategy Engine
Provides optimal play recommendations based on basic strategy and card counting
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

class Action(Enum):
    HIT = "hit"
    STAND = "stand"
    DOUBLE = "double"
    SPLIT = "split"
    SURRENDER = "surrender"
    INSURANCE = "insurance"

@dataclass
class StrategyRecommendation:
    action: Action
    confidence: float  # 0.0 to 1.0
    reasoning: str
    ev_difference: float  # Expected value difference vs other actions
    count_adjustment: Optional[str] = None  # Deviation based on count

class BasicStrategy:
    """
    Implements basic blackjack strategy for 6-8 deck games
    Assumes: Dealer stands on soft 17, double after split allowed
    """
    
    def __init__(self, decks: int = 6, dealer_stands_soft_17: bool = True, 
                 double_after_split: bool = True, surrender_allowed: bool = True):
        self.decks = decks
        self.dealer_stands_soft_17 = dealer_stands_soft_17
        self.double_after_split = double_after_split
        self.surrender_allowed = surrender_allowed
        
        # Basic strategy matrices
        self._build_strategy_tables()
    
    def _build_strategy_tables(self):
        """Build strategy lookup tables"""
        
        # Hard totals (no ace or ace counted as 1)
        # Rows: Player total (5-21), Columns: Dealer up card (2-11, where 11=Ace)
        self.hard_strategy = {
            # Player: Dealer ->  2    3    4    5    6    7    8    9   10    A
            5:  ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
            6:  ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
            7:  ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
            8:  ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
            9:  ['H', 'D', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],
            10: ['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'H', 'H'],
            11: ['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D' if self.dealer_stands_soft_17 else 'H'],
            12: ['H', 'H', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
            13: ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
            14: ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
            15: ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'H', 'R', 'R'],
            16: ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'R', 'R', 'R'],
            17: ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
            18: ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
            19: ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
            20: ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
            21: ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
        }
        
        # Soft totals (ace counted as 11)
        self.soft_strategy = {
            # Player: Dealer ->  2    3    4    5    6    7    8    9   10    A
            13: ['H', 'H', 'H', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],  # A,2
            14: ['H', 'H', 'H', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],  # A,3
            15: ['H', 'H', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],  # A,4
            16: ['H', 'H', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],  # A,5
            17: ['H', 'D', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],  # A,6
            18: ['D' if self.dealer_stands_soft_17 else 'S', 'D', 'D', 'D', 'D', 'S', 'S', 'H', 'H', 'H'],  # A,7
            19: ['S', 'S', 'S', 'S', 'D' if self.dealer_stands_soft_17 else 'S', 'S', 'S', 'S', 'S', 'S'],  # A,8
            20: ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],  # A,9
            21: ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],  # Blackjack
        }
        
        # Pair splitting strategy
        self.split_strategy = {
            # Player: Dealer ->  2    3    4    5    6    7    8    9   10    A
            'A,A': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y'],
            '2,2': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'N', 'N', 'N'],
            '3,3': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'N', 'N', 'N'],
            '4,4': ['N', 'N', 'N', 'Y', 'Y', 'N', 'N', 'N', 'N', 'N'],
            '5,5': ['N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N'],  # Never split 5s
            '6,6': ['Y', 'Y', 'Y', 'Y', 'Y', 'N', 'N', 'N', 'N', 'N'],
            '7,7': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'N', 'N', 'N'],
            '8,8': ['Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y'],
            '9,9': ['Y', 'Y', 'Y', 'Y', 'Y', 'N', 'Y', 'Y', 'N', 'N'],
            '10,10': ['N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N'],  # Never split 10s
        }
    
    def get_recommendation(self, player_total: int, dealer_up_card: int, 
                          is_soft: bool, is_pair: bool, 
                          can_double: bool, can_split: bool,
                          can_surrender: bool) -> Action:
        """Get the basic strategy recommendation"""
        
        # Convert face cards to 10
        if dealer_up_card > 10:
            dealer_up_card = 10
        
        # Handle pairs first
        if is_pair and can_split:
            pair_value = player_total // 2
            pair_key = f"{pair_value},{pair_value}"
            
            if pair_key in self.split_strategy:
                dealer_index = dealer_up_card - 2 if dealer_up_card <= 10 else 9  # Ace is index 9
                should_split = self.split_strategy[pair_key][dealer_index] == 'Y'
                if should_split:
                    return Action.SPLIT
        
        # Handle soft hands
        if is_soft and player_total <= 21:
            if player_total in self.soft_strategy:
                dealer_index = dealer_up_card - 2 if dealer_up_card <= 10 else 9
                action = self.soft_strategy[player_total][dealer_index]
            else:
                action = 'S'  # Default to stand for high soft totals
        # Handle hard hands
        else:
            if player_total < 5:
                action = 'H'
            elif player_total > 21:
                action = 'S'  # Already bust
            elif player_total in self.hard_strategy:
                dealer_index = dealer_up_card - 2 if dealer_up_card <= 10 else 9
                action = self.hard_strategy[player_total][dealer_index]
            else:
                action = 'S'  # Default to stand for high totals
        
        # Convert action code to enum
        if action == 'H':
            return Action.HIT
        elif action == 'S':
            return Action.STAND
        elif action == 'D':
            return Action.DOUBLE if can_double else Action.HIT
        elif action == 'R':
            return Action.SURRENDER if can_surrender and self.surrender_allowed else Action.HIT
        else:
            return Action.STAND

class CardCounter:
    """
    Implements various card counting systems
    """
    
    def __init__(self, system: str = "hi-lo"):
        self.system = system
        self.running_count = 0
        self.cards_seen = 0
        self.decks_remaining = 6  # Default for 6-deck shoe
        
        # Define counting systems
        self.systems = {
            "hi-lo": {
                '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
                '7': 0, '8': 0, '9': 0,
                '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
            },
            "hi-opt-i": {
                '2': 0, '3': 1, '4': 1, '5': 1, '6': 1,
                '7': 0, '8': 0, '9': 0,
                '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': 0
            },
            "wong-halves": {
                '2': 0.5, '3': 1, '4': 1, '5': 1.5, '6': 1,
                '7': 0.5, '8': 0, '9': -0.5,
                '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
            }
        }
        
        self.count_values = self.systems.get(system, self.systems["hi-lo"])
    
    def add_card(self, card_rank: str):
        """Add a card to the count"""
        if card_rank in self.count_values:
            self.running_count += self.count_values[card_rank]
            self.cards_seen += 1
    
    def add_cards(self, cards: List[str]):
        """Add multiple cards to the count"""
        for card in cards:
            self.add_card(card)
    
    def get_true_count(self) -> float:
        """Calculate the true count"""
        cards_remaining = (self.decks_remaining * 52) - self.cards_seen
        decks_remaining = max(0.5, cards_remaining / 52)  # Minimum 0.5 decks
        return self.running_count / decks_remaining
    
    def reset(self):
        """Reset the count for a new shoe"""
        self.running_count = 0
        self.cards_seen = 0
    
    def get_bet_multiplier(self) -> float:
        """Get suggested bet multiplier based on count"""
        true_count = self.get_true_count()
        
        # Kelly Criterion based betting
        if true_count <= 0:
            return 1.0  # Minimum bet
        elif true_count <= 2:
            return 2.0
        elif true_count <= 3:
            return 4.0
        elif true_count <= 4:
            return 6.0
        else:
            return 8.0  # Maximum bet multiplier

class InfinityStrategyEngine:
    """
    Complete strategy engine for Infinity Blackjack
    Combines basic strategy with card counting and deviation plays
    """
    
    def __init__(self):
        self.basic_strategy = BasicStrategy()
        self.card_counter = CardCounter("hi-lo")
        self.hand_history = []
        
        # Deviation indices (when to deviate from basic strategy based on count)
        self.deviations = {
            # Format: (player_total, dealer_card, is_soft): (true_count_threshold, deviation_action)
            (16, 10, False): (0, Action.STAND),  # Stand on 16 vs 10 at TC >= 0
            (15, 10, False): (4, Action.STAND),  # Stand on 15 vs 10 at TC >= 4
            (13, 2, False): (-1, Action.STAND),  # Stand on 13 vs 2 at TC >= -1
            (13, 3, False): (-2, Action.STAND),  # Stand on 13 vs 3 at TC >= -2
            (12, 2, False): (3, Action.STAND),   # Stand on 12 vs 2 at TC >= 3
            (12, 3, False): (2, Action.STAND),   # Stand on 12 vs 3 at TC >= 2
            (12, 4, False): (0, Action.STAND),   # Stand on 12 vs 4 at TC >= 0
            (10, 10, False): (4, Action.DOUBLE), # Double 10 vs 10 at TC >= 4
            (10, 11, False): (4, Action.DOUBLE), # Double 10 vs A at TC >= 4
            (9, 2, False): (1, Action.DOUBLE),   # Double 9 vs 2 at TC >= 1
            (9, 7, False): (3, Action.DOUBLE),   # Double 9 vs 7 at TC >= 3
        }
    
    def analyze_game_state(self, game_state: Dict) -> StrategyRecommendation:
        """
        Analyze the current game state and provide a recommendation
        """
        # Extract relevant information
        player_cards = game_state.get('playerCards', [])
        dealer_cards = game_state.get('dealerCards', [])
        player_total = game_state.get('playerTotal', 0)
        dealer_up_card = self._get_card_value(dealer_cards[0]) if dealer_cards else 0
        is_soft = game_state.get('playerSoft', False)
        
        # Check for pairs
        is_pair = len(player_cards) == 2 and self._get_card_value(player_cards[0]) == self._get_card_value(player_cards[1])
        
        # Get available actions
        actions = game_state.get('actions', {})
        can_hit = actions.get('canHit', False)
        can_stand = actions.get('canStand', False)
        can_double = actions.get('canDouble', False)
        can_split = actions.get('canSplit', False)
        can_surrender = False  # Infinity typically doesn't offer surrender
        
        # Update card count
        for card in player_cards + dealer_cards:
            self.card_counter.add_card(card.get('rank', ''))
        
        # Get true count
        true_count = self.card_counter.get_true_count()
        
        # Check for count-based deviations
        deviation_action = self._check_deviations(player_total, dealer_up_card, is_soft, true_count)
        
        if deviation_action:
            # Use deviation play
            action = deviation_action
            reasoning = f"Deviation play based on true count of {true_count:.1f}"
            confidence = min(0.9 + abs(true_count) * 0.02, 1.0)  # Higher count = higher confidence
            count_adjustment = f"TC: {true_count:.1f} - Deviating from basic strategy"
        else:
            # Use basic strategy
            action = self.basic_strategy.get_recommendation(
                player_total, dealer_up_card, is_soft, is_pair,
                can_double, can_split, can_surrender
            )
            reasoning = "Basic strategy recommendation"
            confidence = 0.85
            count_adjustment = f"TC: {true_count:.1f} - Following basic strategy"
        
        # Calculate expected value difference (simplified)
        ev_difference = self._calculate_ev_difference(action, player_total, dealer_up_card)
        
        return StrategyRecommendation(
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            ev_difference=ev_difference,
            count_adjustment=count_adjustment
        )
    
    def _get_card_value(self, card: Dict) -> int:
        """Get the blackjack value of a card"""
        rank = card.get('rank', '')
        if rank == 'A':
            return 11
        elif rank in ['K', 'Q', 'J']:
            return 10
        else:
            try:
                return int(rank)
            except:
                return 0
    
    def _check_deviations(self, player_total: int, dealer_card: int, 
                         is_soft: bool, true_count: float) -> Optional[Action]:
        """Check if we should deviate from basic strategy based on count"""
        key = (player_total, dealer_card, is_soft)
        
        if key in self.deviations:
            threshold, deviation_action = self.deviations[key]
            if true_count >= threshold:
                return deviation_action
        
        return None
    
    def _calculate_ev_difference(self, action: Action, player_total: int, 
                                dealer_up_card: int) -> float:
        """
        Calculate simplified expected value difference
        This is a simplified calculation for demonstration
        """
        # Basic EV estimates (these would be more complex in reality)
        if action == Action.STAND:
            if player_total >= 17:
                return 0.0
            else:
                return -0.15  # Standing on low total
        elif action == Action.HIT:
            if player_total <= 11:
                return 0.10  # Can't bust
            elif player_total >= 17:
                return -0.20  # High bust probability
            else:
                return 0.0
        elif action == Action.DOUBLE:
            if player_total in [10, 11]:
                return 0.15  # Strong double
            elif player_total == 9:
                return 0.05
            else:
                return -0.10
        elif action == Action.SPLIT:
            return 0.05  # Generally positive
        else:
            return 0.0
    
    def get_bet_recommendation(self, bankroll: float, min_bet: float, max_bet: float) -> Dict:
        """Get betting recommendation based on count"""
        true_count = self.card_counter.get_true_count()
        multiplier = self.card_counter.get_bet_multiplier()
        
        # Calculate bet size
        base_bet = min_bet
        recommended_bet = min(base_bet * multiplier, max_bet)
        
        # Kelly percentage (simplified)
        kelly_fraction = max(0, (true_count - 1) * 0.01)  # 1% edge per true count above 1
        kelly_bet = bankroll * kelly_fraction
        
        # Use the smaller of Kelly bet and table max
        final_bet = min(recommended_bet, kelly_bet, max_bet)
        
        return {
            'recommended_bet': final_bet,
            'multiplier': multiplier,
            'true_count': true_count,
            'kelly_fraction': kelly_fraction,
            'confidence': 'High' if true_count > 2 else 'Medium' if true_count > 0 else 'Low',
            'reason': f"True count: {true_count:.1f}, Multiplier: {multiplier}x"
        }
    
    def reset_shoe(self):
        """Reset for a new shoe"""
        self.card_counter.reset()
        self.hand_history.clear()
    
    def add_hand_to_history(self, hand_data: Dict):
        """Add a completed hand to history for analysis"""
        self.hand_history.append({
            'timestamp': hand_data.get('timestamp'),
            'player_total': hand_data.get('playerTotal'),
            'dealer_total': hand_data.get('dealerTotal'),
            'action_taken': hand_data.get('actionTaken'),
            'result': hand_data.get('result'),
            'bet_amount': hand_data.get('betAmount'),
            'true_count': self.card_counter.get_true_count()
        })
