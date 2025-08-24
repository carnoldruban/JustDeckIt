#!/usr/bin/env python3
"""
Simple test script to verify the blackjack tracker system works correctly.
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")
    
    try:
        from shoe import Shoe
        print("✅ shoe.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing shoe.py: {e}")
        return False
    
    try:
        from shoe_manager import ShoeManager
        print("✅ shoe_manager.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing shoe_manager.py: {e}")
        return False
    
    try:
        from database_manager import DatabaseManager
        print("✅ database_manager.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing database_manager.py: {e}")
        return False
    
    try:
        from card_counter import HiLoCounter, WongHalvesCounter
        print("✅ card_counter.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing card_counter.py: {e}")
        return False
    
    try:
        from strategy import get_strategy_action, get_bet_recommendation
        print("✅ strategy.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing strategy.py: {e}")
        return False
    
    try:
        from shuffling import perform_full_shuffle
        print("✅ shuffling.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing shuffling.py: {e}")
        return False
    
    try:
        from analytics_engine import AnalyticsEngine
        print("✅ analytics_engine.py imported successfully")
    except Exception as e:
        print(f"❌ Error importing analytics_engine.py: {e}")
        return False
    
    return True

def test_shoe_operations():
    """Test basic shoe operations."""
    print("\nTesting shoe operations...")
    
    try:
        from shoe import Shoe
        
        # Test shoe creation
        shoe = Shoe()
        print("✅ Shoe created successfully")
        
        # Test card removal
        shoe.undealt_cards = ['2H', '3D', '4C', '5S', '6H', '7D', '8C', '9S', 'TH', 'JD']
        removed = shoe.remove_cards(['2', '3', '4'])
        print(f"✅ Removed {len(removed)} cards: {removed}")
        
        # Test zone info
        zone_info = shoe.get_zone_info(4)
        print(f"✅ Zone info calculated: {len(zone_info)} zones")
        
        return True
    except Exception as e:
        print(f"❌ Error in shoe operations: {e}")
        return False

def test_shoe_manager():
    """Test shoe manager operations."""
    print("\nTesting shoe manager...")
    
    try:
        from shoe_manager import ShoeManager
        from database_manager import DatabaseManager
        
        db_manager = DatabaseManager(":memory:")  # Use in-memory database for testing
        shoe_manager = ShoeManager(db_manager)
        
        # Test setting active shoe
        shoe_manager.set_active_shoe("Shoe 1")
        print("✅ Active shoe set successfully")
        
        # Test getting active shoe
        active_shoe = shoe_manager.get_active_shoe()
        if active_shoe:
            print("✅ Active shoe retrieved successfully")
        else:
            print("❌ Failed to get active shoe")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error in shoe manager: {e}")
        return False

def test_card_counting():
    """Test card counting systems."""
    print("\nTesting card counting...")
    
    try:
        from card_counter import HiLoCounter, WongHalvesCounter
        
        # Test Hi-Lo counter
        hilo = HiLoCounter()
        hilo.process_cards(['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'])
        running_count = hilo.get_running_count()
        true_count = hilo.get_true_count()
        print(f"✅ Hi-Lo: RC={running_count}, TC={true_count:.2f}")
        
        # Test Wong Halves counter
        wong = WongHalvesCounter()
        wong.process_cards(['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'])
        running_count = wong.get_running_count()
        true_count = wong.get_true_count()
        print(f"✅ Wong Halves: RC={running_count:.1f}, TC={true_count:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Error in card counting: {e}")
        return False

def test_strategy():
    """Test strategy recommendations."""
    print("\nTesting strategy...")
    
    try:
        from strategy import get_strategy_action, get_bet_recommendation
        
        # Test bet recommendation
        bet_rec = get_bet_recommendation(2.5)
        print(f"✅ Bet recommendation for TC=2.5: {bet_rec}")
        
        # Test strategy action - fix the parameter format
        action = get_strategy_action(['T', '6'], '7', 1.0)  # 16 vs 7
        print(f"✅ Strategy action for 16 vs 7: {action}")
        
        return True
    except Exception as e:
        print(f"❌ Error in strategy: {e}")
        return False

def test_shuffling():
    """Test shuffling algorithm."""
    print("\nTesting shuffling...")
    
    try:
        from shuffling import perform_full_shuffle
        
        # Test shuffle with sample cards
        test_cards = ['2H', '3D', '4C', '5S', '6H', '7D', '8C', '9S', 'TH', 'JD']
        shuffled = perform_full_shuffle(test_cards, num_iterations=2, num_chunks=4)
        
        if len(shuffled) == len(test_cards):
            print(f"✅ Shuffle completed: {len(shuffled)} cards")
        else:
            print(f"❌ Shuffle failed: expected {len(test_cards)}, got {len(shuffled)}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error in shuffling: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Blackjack Tracker System Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_shoe_operations,
        test_shoe_manager,
        test_card_counting,
        test_strategy,
        test_shuffling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"❌ Test {test.__name__} failed")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
