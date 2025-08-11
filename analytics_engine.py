"""
Analytics Engine for Blackjack Tracker
Provides comprehensive analysis and decision support for profitable blackjack play.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class AnalyticsEngine:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.current_session_id = None
        
    def start_session_tracking(self, shoe_name: str) -> int:
        """Starts tracking a new shoe session."""
        self.current_session_id = self.db_manager.start_shoe_session(shoe_name)
        return self.current_session_id
    
    def end_session_tracking(self, final_stats: Dict = None):
        """Ends the current shoe session tracking."""
        if self.current_session_id:
            self.db_manager.end_shoe_session(self.current_session_id, final_stats)
            self.current_session_id = None
    
    def validate_prediction(self, card_position: int, predicted_card: str, actual_card: str, round_id: int):
        """Validates a shuffle prediction against actual dealt card."""
        if not self.current_session_id:
            return
            
        # Calculate position offset if prediction was wrong
        position_offset = 0
        if predicted_card != actual_card:
            # This would need implementation based on the shuffle tracking system
            position_offset = self._calculate_position_offset(predicted_card, actual_card)
        
        self.db_manager.save_prediction_validation(
            self.current_session_id, round_id, card_position, 
            predicted_card, actual_card, position_offset
        )
    
    def _calculate_position_offset(self, predicted_card: str, actual_card: str) -> int:
        """Calculates how far off the prediction was in the shoe."""
        # This is a placeholder - would need access to the current shoe state
        # to determine where the actual card was in the predicted sequence
        return 0
    
    def track_card_dealt(self, round_id: int, card_value: str, dealt_position: int, 
                        seat_number: Optional[int], card_type: str, dealing_order: int):
        """Tracks each individual card as it's dealt."""
        if not self.current_session_id:
            return
            
        self.db_manager.save_card_tracking(
            self.current_session_id, round_id, card_value, dealt_position,
            seat_number, card_type, dealing_order
        )
    
    def update_seat_performance(self, seat_number: int, result: str):
        """Updates performance statistics for a seat."""
        if not self.current_session_id:
            return
            
        self.db_manager.update_seat_performance(self.current_session_id, seat_number, result)
    
    def get_real_time_predictions(self, shoe_cards: List, dealt_cards: List) -> List[str]:
        """
        Returns the next 5 card predictions as ranges: Low/Mid/High
        Low: 2-5, Mid: 6-9, High: 10-A
        """
        if not shoe_cards:
            return ["Unknown"] * 5
        
        # Get next 5 cards from the shoe
        next_cards = shoe_cards[:5] if len(shoe_cards) >= 5 else shoe_cards
        predictions = []
        
        for card in next_cards:
            card_value = self._extract_card_value(str(card))
            range_category = self._get_card_range(card_value)
            predictions.append(range_category)
        
        # Pad with unknowns if less than 5 cards
        while len(predictions) < 5:
            predictions.append("Unknown")
        
        return predictions
    
    def _extract_card_value(self, card_str: str) -> str:
        """Extracts the rank from a card string."""
        if hasattr(card_str, 'rank_str'):
            return card_str.rank_str
        elif len(card_str) >= 1:
            return card_str[0]
        return "?"
    
    def _get_card_range(self, card_value: str) -> str:
        """Categorizes a card into Low/Mid/High range."""
        if card_value in ['2', '3', '4', '5']:
            return "Low"
        elif card_value in ['6', '7', '8', '9']:
            return "Mid"
        elif card_value in ['10', 'T', 'J', 'Q', 'K', 'A']:
            return "High"
        else:
            return "Unknown"
    
    def get_shoe_performance_analysis(self, hours_back: int = 24) -> Dict:
        """Gets comprehensive shoe performance analysis for decision making."""
        if not self.db_manager.conn:
            return {}
        
        cursor = self.db_manager.conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        # Get shoe performance stats
        cursor.execute("""
            SELECT 
                shoe_name,
                AVG(win_rate) as avg_win_rate,
                COUNT(*) as sessions_count,
                AVG(total_rounds) as avg_rounds,
                SUM(player_wins) as total_player_wins,
                SUM(dealer_wins) as total_dealer_wins,
                SUM(pushes) as total_pushes
            FROM shoe_sessions 
            WHERE start_time >= ? AND status = 'completed'
            GROUP BY shoe_name
            ORDER BY avg_win_rate DESC
        """, (cutoff_time,))
        
        shoe_stats = cursor.fetchall()
        
        # Get seat performance stats
        cursor.execute("""
            SELECT 
                sp.seat_number,
                AVG(sp.win_rate) as avg_win_rate,
                SUM(sp.rounds_played) as total_rounds,
                SUM(sp.wins) as total_wins,
                COUNT(DISTINCT ss.id) as sessions_count
            FROM seat_performance sp
            JOIN shoe_sessions ss ON sp.shoe_session_id = ss.id
            WHERE ss.start_time >= ? AND ss.status = 'completed'
            GROUP BY sp.seat_number
            ORDER BY avg_win_rate DESC
        """, (cutoff_time,))
        
        seat_stats = cursor.fetchall()
        
        # Get prediction accuracy
        cursor.execute("""
            SELECT 
                AVG(CASE WHEN prediction_correct = 1 THEN 1.0 ELSE 0.0 END) as accuracy,
                COUNT(*) as total_predictions
            FROM prediction_validation pv
            JOIN shoe_sessions ss ON pv.shoe_session_id = ss.id
            WHERE ss.start_time >= ?
        """, (cutoff_time,))
        
        prediction_stats = cursor.fetchone()
        
        return {
            'shoe_performance': [
                {
                    'name': row[0],
                    'win_rate': row[1],
                    'sessions': row[2],
                    'avg_rounds': row[3],
                    'player_wins': row[4],
                    'dealer_wins': row[5],
                    'pushes': row[6]
                } for row in shoe_stats
            ],
            'seat_performance': [
                {
                    'seat_number': row[0],
                    'win_rate': row[1],
                    'total_rounds': row[2],
                    'total_wins': row[3],
                    'sessions': row[4]
                } for row in seat_stats
            ],
            'prediction_accuracy': {
                'accuracy': prediction_stats[0] if prediction_stats[0] else 0.0,
                'total_predictions': prediction_stats[1] if prediction_stats[1] else 0
            },
            'analysis_period': f"Last {hours_back} hours",
            'generated_at': datetime.now().isoformat()
        }
    
    def get_decision_recommendations(self) -> Dict:
        """Provides actionable recommendations for playing decisions."""
        analysis = self.get_shoe_performance_analysis()
        
        recommendations = {
            'should_play': False,
            'best_shoe': None,
            'best_seat': None,
            'confidence_level': 'Low',
            'reasons': []
        }
        
        # Analyze shoe performance
        shoe_perf = analysis.get('shoe_performance', [])
        if shoe_perf:
            best_shoe = shoe_perf[0]
            if best_shoe['win_rate'] > 0.55:  # 55% win rate threshold
                recommendations['should_play'] = True
                recommendations['best_shoe'] = best_shoe['name']
                recommendations['confidence_level'] = 'High' if best_shoe['win_rate'] > 0.60 else 'Medium'
                recommendations['reasons'].append(f"Shoe '{best_shoe['name']}' has {best_shoe['win_rate']:.1%} win rate")
        
        # Analyze seat performance
        seat_perf = analysis.get('seat_performance', [])
        if seat_perf:
            best_seat = seat_perf[0]
            if best_seat['win_rate'] > 0.55:
                recommendations['best_seat'] = best_seat['seat_number']
                recommendations['reasons'].append(f"Seat {best_seat['seat_number']} has {best_seat['win_rate']:.1%} win rate")
        
        # Check prediction accuracy
        pred_acc = analysis.get('prediction_accuracy', {})
        if pred_acc.get('accuracy', 0) > 0.70:
            recommendations['reasons'].append(f"Prediction accuracy is {pred_acc['accuracy']:.1%}")
        elif pred_acc.get('accuracy', 0) < 0.50:
            recommendations['confidence_level'] = 'Low'
            recommendations['reasons'].append("Low prediction accuracy - exercise caution")
        
        return recommendations
    
    def get_hourly_performance_trends(self, days_back: int = 7) -> Dict:
        """Gets performance trends by hour of day for optimal play timing."""
        if not self.db_manager.conn:
            return {}
        
        cursor = self.db_manager.conn.cursor()
        cutoff_time = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        cursor.execute("""
            SELECT 
                strftime('%H', start_time) as hour,
                AVG(win_rate) as avg_win_rate,
                COUNT(*) as session_count,
                AVG(total_rounds) as avg_rounds
            FROM shoe_sessions 
            WHERE start_time >= ? AND status = 'completed' AND win_rate IS NOT NULL
            GROUP BY strftime('%H', start_time)
            ORDER BY avg_win_rate DESC
        """, (cutoff_time,))
        
        hourly_data = cursor.fetchall()
        
        return {
            'hourly_trends': [
                {
                    'hour': int(row[0]),
                    'win_rate': row[1],
                    'sessions': row[2],
                    'avg_rounds': row[3]
                } for row in hourly_data
            ],
            'best_hours': [int(row[0]) for row in hourly_data[:3]],  # Top 3 hours
            'analysis_period': f"Last {days_back} days"
        }
    
    def export_analysis_report(self, filename: str = None) -> str:
        """Exports a comprehensive analysis report to JSON file."""
        if not filename:
            filename = f"blackjack_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'shoe_analysis': self.get_shoe_performance_analysis(),
            'recommendations': self.get_decision_recommendations(),
            'hourly_trends': self.get_hourly_performance_trends(),
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filename
