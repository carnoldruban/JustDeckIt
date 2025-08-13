"""
Test script to verify the simulation system is working correctly
"""

import json
import queue
import time
from scraper_sim import Scraper

def test_simulation_system():
    """Test the complete simulation system"""
    print("🎮 TESTING BLACKJACK SIMULATION SYSTEM")
    print("=" * 60)
    
    # Test 1: Check if test data exists
    print("\n1. Checking test data file...")
    try:
        with open("blackjack_test_data_300rounds.json", 'r') as f:
            test_data = json.load(f)
        print(f"   ✅ Test data loaded: {len(test_data)} rounds")
    except FileNotFoundError:
        print("   ❌ Test data file not found!")
        return False
    except Exception as e:
        print(f"   ❌ Error loading test data: {e}")
        return False
    
    # Test 2: Test simulation scraper
    print("\n2. Testing simulation scraper...")
    try:
        test_queue = queue.Queue()
        scraper = Scraper(test_queue, test_file="blackjack_test_data_300rounds.json")
        
        # Start scraper for a few seconds
        scraper.start()
        time.sleep(3)  # Let it run for 3 seconds
        scraper.stop()
        
        # Check results
        rounds_received = 0
        sample_data = None
        while not test_queue.empty():
            data = test_queue.get()
            rounds_received += 1
            if rounds_received == 1:
                sample_data = data
        
        print(f"   ✅ Scraper processed {rounds_received} rounds")
        
        if sample_data:
            print(f"   ✅ Sample game ID: {sample_data.get('gameId', 'N/A')}")
            print(f"   ✅ Sample has dealer: {'dealer' in sample_data}")
            print(f"   ✅ Sample has seats: {'seats' in sample_data}")
        
    except Exception as e:
        print(f"   ❌ Scraper test failed: {e}")
        return False
    
    # Test 3: Check database manager
    print("\n3. Testing simulation database...")
    try:
        from database_manager_sim import DBManager
        db = DBManager()
        
        # Test connection
        if db.conn:
            print("   ✅ Simulation database connected")
            
            # Test saving a sample game
            if sample_data:
                db.save_game_state(sample_data)
                print("   ✅ Sample game saved to simulation DB")
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False
    
    # Test 4: Check file structure
    print("\n4. Checking simulation file structure...")
    import os
    
    required_files = [
        "scraper_sim.py",
        "database_manager_sim.py", 
        "tracker_app_sim.py",
        "generate_test_data.py",
        "blackjack_test_data_300rounds.json"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING!")
            return False
    
    print("\n🎉 SIMULATION SYSTEM TEST COMPLETE!")
    print("=" * 60)
    print("✅ All tests passed!")
    print("🎮 Simulation system is ready to use!")
    print("🚀 Run 'python tracker_app_sim.py' to start the simulation")
    
    return True

if __name__ == "__main__":
    test_simulation_system()
