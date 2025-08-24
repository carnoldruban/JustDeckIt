"""
Prediction Validator for Blackjack Tracker
Compares shuffle predictions against actual cards dealt and learns patterns.
"""

from typing import List, Dict, Tuple, Optional
from collections import deque
import json
from datetime import datetime

class PredictionValidator:
    def __init__(self, analytics_engine):
        self.analytics_engine = analytics_engine
        self.prediction_history = deque(maxlen=1000)  # Keep last 1000 predictions
        self.pattern_database = {}
        self.current_round_predictions = []
        self.current_round_actuals = []
        self.dealing_order_map = {
            # Dealing order: Seat 6 -> 5 -> 4 -> 3 -> 2 -> 1 -> 0 -> Dealer face up
            # Then second cards: Seat 6 -> 5 -> 4 -> 3 -> 2 -> 1 -> 0 -> Dealer hole
            1: {'seat': 6, 'card_num': 1, 'description': 'Seat 6 First Card'},
            2: {'seat': 5, 'card_num': 1, 'description': 'Seat 5 First Card'},
            3: {'seat': 4, 'card_num': 1, 'description': 'Seat 4 First Card'},
            4: {'seat': 3, 'card_num': 1, 'description': 'Seat 3 First Card'},
            5: {'seat': 2, 'card_num': 1, 'description': 'Seat 2 First Card'},
            6: {'seat': 1, 'card_num': 1, 'description': 'Seat 1 First Card'},
            7: {'seat': 0, 'card_num': 1, 'description': 'Seat 0 First Card'},
            8: {'seat': -1, 'card_num': 1, 'description': 'Dealer Face Up Card'},
            9: {'seat': 6, 'card_num': 2, 'description': 'Seat 6 Second Card'},
            10: {'seat': 5, 'card_num': 2, 'description': 'Seat 5 Second Card'},
            11: {'seat': 4, 'card_num': 2, 'description': 'Seat 4 Second Card'},
            12: {'seat': 3, 'card_num': 2, 'description': 'Seat 3 Second Card'},
            13: {'seat': 2, 'card_num': 2, 'description': 'Seat 2 Second Card'},
            14: {'seat': 1, 'card_num': 2, 'description': 'Seat 1 Second Card'},
            15: {'seat': 0, 'card_num': 2, 'description': 'Seat 0 Second Card'},
            16: {'seat': -1, 'card_num': 2, 'description': 'Dealer Hole Card'},
        }
    
    def start_round_prediction(self, predicted_shoe_cards: List):
        """Starts prediction tracking for a new round."""
        self.current_round_predictions = predicted_shoe_cards[:16] if len(predicted_shoe_cards) >= 16 else predicted_shoe_cards
        self.current_round_actuals = []
        
        print(f"[Prediction] Started tracking round with {len(self.current_round_predictions)} predicted cards")
    
    def add_dealt_card(self, card_value: str, dealing_position: int, seat_number: Optional[int] = None):
        """Adds an actually dealt card to compare against predictions."""
        self.current_round_actuals.append({
            'card': card_value,
            'position': dealing_position,
            'seat': seat_number,
            'timestamp': datetime.now().isoformat()
        })
        
        # Validate this card against prediction if we have one
        if dealing_position <= len(self.current_round_predictions):
            predicted_card = str(self.current_round_predictions[dealing_position - 1])
            self._validate_single_prediction(dealing_position, predicted_card, card_value)
    
    def _validate_single_prediction(self, position: int, predicted_card: str, actual_card: str):
        """Validates a single card prediction."""
        # Extract card rank for comparison
        predicted_rank = self._extract_card_rank(predicted_card)
        actual_rank = self._extract_card_rank(actual_card)
        
        is_correct = predicted_rank == actual_rank
        position_offset = 0
        
        if not is_correct:
            # Find where the actual card was in our prediction sequence
            position_offset = self._find_card_position_offset(actual_rank, position)
        
        # Record the validation
        validation_record = {
            'position': position,
            'predicted': predicted_rank,
            'actual': actual_rank,
            'correct': is_correct,
            'offset': position_offset,
            'timestamp': datetime.now().isoformat(),
            'dealing_info': self.dealing_order_map.get(position, {'description': f'Position {position}'})
        }
        
        self.prediction_history.append(validation_record)
        
        # Save to database if analytics engine is available
        if self.analytics_engine and self.analytics_engine.current_session_id:
            # This would need a round_id - placeholder for now
            round_id = 1  # Would get this from the current game state
            self.analytics_engine.validate_prediction(position, predicted_rank, actual_rank, round_id)
        
        print(f"[Prediction] Position {position} ({validation_record['dealing_info']['description']}): "
              f"Predicted {predicted_rank}, Got {actual_rank} {'✓' if is_correct else '✗'}")
        
        if not is_correct and position_offset != 0:
            print(f"[Prediction] Card was {abs(position_offset)} positions {'ahead' if position_offset > 0 else 'behind'}")
    
    def _extract_card_rank(self, card_str: str) -> str:
        """Extracts rank from card string representation."""
        if hasattr(card_str, 'rank_str'):
            return card_str.rank_str
        elif isinstance(card_str, str) and len(card_str) >= 1:
            return card_str[0].upper()
        else:
            return str(card_str)[:1].upper()
    
    def _find_card_position_offset(self, actual_rank: str, predicted_position: int) -> int:
        """Finds where the actual card was in the predicted sequence."""
        # Look in a window around the predicted position
        search_window = 10  # Search +/- 10 positions
        start_idx = max(0, predicted_position - search_window - 1)
        end_idx = min(len(self.current_round_predictions), predicted_position + search_window)
        
        for i in range(start_idx, end_idx):
            if i == predicted_position - 1:  # Skip the original position
                continue
            
            predicted_card = str(self.current_round_predictions[i])
            predicted_rank = self._extract_card_rank(predicted_card)
            
            if predicted_rank == actual_rank:
                return (i + 1) - predicted_position  # +1 because positions are 1-indexed
        
        return 0  # Card not found in search window
    
    def end_round_analysis(self):
        """Completes the round and analyzes overall prediction performance."""
        if not self.current_round_actuals:
            return
        
        total_predictions = len(self.current_round_actuals)
        correct_predictions = sum(1 for record in self.prediction_history 
                                if record.get('correct', False) and 
                                record.get('timestamp', '').startswith(datetime.now().strftime('%Y-%m-%d')))
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        
        print(f"[Prediction] Round complete: {correct_predictions}/{total_predictions} correct ({accuracy:.1%})")
        
        # Analyze patterns in errors
        self._analyze_error_patterns()
        
        # Reset for next round
        self.current_round_predictions = []
        self.current_round_actuals = []
    
    def _analyze_error_patterns(self):
        """Analyzes patterns in prediction errors to improve future shuffling."""
        recent_errors = [record for record in self.prediction_history 
                        if not record.get('correct', True) and record.get('offset', 0) != 0]
        
        if len(recent_errors) < 5:  # Need enough data
            return
        
        # Analyze offset patterns
        offset_pattern = {}
        position_pattern = {}
        
        for error in recent_errors[-20:]:  # Last 20 errors
            offset = error.get('offset', 0)
            position = error.get('position', 0)
            
            offset_pattern[offset] = offset_pattern.get(offset, 0) + 1
            position_pattern[position] = position_pattern.get(position, 0) + 1
        
        # Find most common offset patterns
        if offset_pattern:
            most_common_offset = max(offset_pattern, key=offset_pattern.get)
            if offset_pattern[most_common_offset] >= 3:
                print(f"[Pattern] Detected systematic offset: {most_common_offset} positions "
                      f"(occurred {offset_pattern[most_common_offset]} times)")
                
                # Save pattern to database for future use
                self._save_pattern('systematic_offset', {
                    'offset': most_common_offset,
                    'frequency': offset_pattern[most_common_offset],
                    'confidence': offset_pattern[most_common_offset] / len(recent_errors)
                })
    
    def _save_pattern(self, pattern_type: str, pattern_data: Dict):
        """Saves a discovered pattern for future reference."""
        pattern_key = f"{pattern_type}_{datetime.now().strftime('%Y%m%d')}"
        
        if pattern_key not in self.pattern_database:
            self.pattern_database[pattern_key] = {
                'type': pattern_type,
                'data': pattern_data,
                'discovered_at': datetime.now().isoformat(),
                'usage_count': 0
            }
            
            print(f"[Pattern] Saved new pattern: {pattern_type} with data: {pattern_data}")
    
    def get_prediction_accuracy_stats(self, last_n_rounds: int = 10) -> Dict:
        """Gets prediction accuracy statistics for the last N rounds."""
        if not self.prediction_history:
            return {'accuracy': 0.0, 'total_predictions': 0, 'trends': 'No data'}
        
        recent_predictions = list(self.prediction_history)[-last_n_rounds * 16:]  # Assume 16 cards per round
        
        if not recent_predictions:
            return {'accuracy': 0.0, 'total_predictions': 0, 'trends': 'Insufficient data'}
        
        total = len(recent_predictions)
        correct = sum(1 for p in recent_predictions if p.get('correct', False))
        accuracy = correct / total if total > 0 else 0.0
        
        # Analyze trends by position
        position_accuracy = {}
        for prediction in recent_predictions:
            pos = prediction.get('position', 0)
            if pos not in position_accuracy:
                position_accuracy[pos] = {'correct': 0, 'total': 0}
            
            position_accuracy[pos]['total'] += 1
            if prediction.get('correct', False):
                position_accuracy[pos]['correct'] += 1
        
        # Find best and worst positions
        position_rates = {pos: stats['correct'] / stats['total'] 
                         for pos, stats in position_accuracy.items() if stats['total'] > 0}
        
        best_position = max(position_rates, key=position_rates.get) if position_rates else None
        worst_position = min(position_rates, key=position_rates.get) if position_rates else None
        
        return {
            'accuracy': accuracy,
            'total_predictions': total,
            'correct_predictions': correct,
            'best_position': best_position,
            'worst_position': worst_position,
            'position_accuracy': position_accuracy,
            'trends': 'Improving' if accuracy > 0.6 else 'Needs attention' if accuracy < 0.4 else 'Stable'
        }
    
    def apply_learned_patterns(self, predicted_sequence: List) -> List:
        """Applies learned patterns to improve future predictions."""
        if not self.pattern_database or not predicted_sequence:
            return predicted_sequence
        
        improved_sequence = predicted_sequence.copy()
        
        # Apply systematic offset corrections
        for pattern_key, pattern_info in self.pattern_database.items():
            if pattern_info['type'] == 'systematic_offset' and pattern_info['data'].get('confidence', 0) > 0.6:
                offset = pattern_info['data'].get('offset', 0)
                if offset != 0 and abs(offset) <= 5:  # Only apply small, reliable offsets
                    print(f"[Pattern] Applying learned offset correction: {offset} positions")
                    # This would apply the offset to the sequence
                    # Implementation depends on how the shuffle tracking works
                    pattern_info['usage_count'] += 1
        
        return improved_sequence
    
    def export_prediction_analysis(self, filename: str = None) -> str:
        """Exports detailed prediction analysis to file."""
        if not filename:
            filename = f"prediction_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        analysis = {
            'generated_at': datetime.now().isoformat(),
            'total_predictions': len(self.prediction_history),
            'accuracy_stats': self.get_prediction_accuracy_stats(),
            'discovered_patterns': self.pattern_database,
            'recent_predictions': list(self.prediction_history)[-50:],  # Last 50 predictions
            'dealing_order_reference': self.dealing_order_map
        }
        
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return filename
