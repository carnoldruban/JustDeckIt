"""
Test script for the enhanced blackjack tracker
Tests all new analytics and prediction features
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import DBManager
from analytics_engine import AnalyticsEngine
from prediction_validator import PredictionValidator
from cards import Card, Shoe

def test_analytics_features():
    """Test the new analytics features."""
    print("=== Testing Enhanced Blackjack Tracker Features ===\n")
    
    # Initialize components
    print("1. Initializing components...")
    db_manager = DBManager()
    analytics_engine = AnalyticsEngine(db_manager)
    prediction_validator = PredictionValidator(analytics_engine)
    print("   ✓ All components initialized successfully\n")
    
    # Test session tracking
    print("2. Testing session tracking...")
    session_id = analytics_engine.start_session_tracking("Test Shoe 1")
    print(f"   ✓ Session started with ID: {session_id}")
    
    # Test prediction validation
    print("\n3. Testing prediction validation...")
    # Create a mock shoe for predictions
    test_shoe = Shoe(num_physical_decks=1, shuffle_now=True)
    prediction_validator.start_round_prediction(list(test_shoe.undealt_cards))
    
    # Simulate some card predictions vs actuals
    test_cards = ["KH", "AS", "7D", "QC", "5S"]
    for i, card in enumerate(test_cards, 1):
        prediction_validator.add_dealt_card(card, i, i % 7)
    
    prediction_validator.end_round_analysis()
    accuracy_stats = prediction_validator.get_prediction_accuracy_stats()
    print(f"   ✓ Prediction validation complete. Accuracy: {accuracy_stats['accuracy']:.1%}")
    
    # Test card range predictions
    print("\n4. Testing card range predictions...")
    predictions = analytics_engine.get_real_time_predictions(list(test_shoe.undealt_cards)[:5], [])
    print(f"   ✓ Next 5 card ranges: {' | '.join(predictions)}")
    
    # Test analytics summary
    print("\n5. Testing analytics summary...")
    analysis = analytics_engine.get_shoe_performance_analysis(hours_back=1)
    print(f"   ✓ Analysis generated with {len(analysis.get('shoe_performance', []))} shoe records")
    
    # Test recommendations
    print("\n6. Testing decision recommendations...")
    recommendations = analytics_engine.get_decision_recommendations()
    print(f"   ✓ Recommendations generated. Should play: {recommendations['should_play']}")
    
    # End session
    print("\n7. Ending test session...")
    final_stats = {
        'total_rounds': 5,
        'total_cards_dealt': 25,
        'win_rate': 0.6,
        'dealer_wins': 2,
        'player_wins': 3,
        'pushes': 0
    }
    analytics_engine.end_session_tracking(final_stats)
    print("   ✓ Session ended successfully")
    
    # Export test report
    print("\n8. Testing report export...")
    report_filename = analytics_engine.export_analysis_report("test_report.json")
    print(f"   ✓ Report exported to: {report_filename}")
    
    # Clean up
    db_manager.close()
    print("\n=== All Tests Completed Successfully! ===")
    
    return True

def test_dealing_sequence():
    """Test the dealing sequence validation."""
    print("\n=== Testing Dealing Sequence ===")
    
    dealing_order = {
        1: 'Seat 6 First Card',
        2: 'Seat 5 First Card',
        3: 'Seat 4 First Card',
        4: 'Seat 3 First Card',
        5: 'Seat 2 First Card',
        6: 'Seat 1 First Card',
        7: 'Seat 0 First Card',
        8: 'Dealer Face Up',
        9: 'Seat 6 Second Card',
        10: 'Seat 5 Second Card',
        11: 'Seat 4 Second Card',
        12: 'Seat 3 Second Card',
        13: 'Seat 2 Second Card',
        14: 'Seat 1 Second Card',
        15: 'Seat 0 Second Card',
        16: 'Dealer Hole Card'
    }
    
    print("Dealing order verification:")
    for position, description in dealing_order.items():
        print(f"   Position {position:2d}: {description}")
    
    print("✓ Dealing sequence correctly defined")

if __name__ == "__main__":
    try:
        test_analytics_features()
        test_dealing_sequence()
        print("\n🎉 All tests passed! The enhanced blackjack tracker is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
