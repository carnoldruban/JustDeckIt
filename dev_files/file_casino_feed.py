#!/usr/bin/env python3
"""
File-based Casino Feed - Reads 3-hour data file and feeds to tracker app
Phase 1: Fast forward through first 2 hours (120 rounds)
Phase 2: Real-time feed for last 1 hour (60 rounds)
"""

import json
import time
import threading
from datetime import datetime

class FileCasinoFeed:
    def __init__(self, data_queue, data_file="3hour_casino_data.json"):
        self.data_queue = data_queue
        self.data_file = data_file
        self.is_running = False
        self.all_data = []
        self.current_round = 0
        self.fast_forward_complete = False
        self.speed_mode = "fast"  # "fast" or "realtime"
        self.speed_lock = threading.Lock()
        
    def toggle_speed(self):
        """Toggle between fast and real-time speed"""
        with self.speed_lock:
            if self.speed_mode == "fast":
                self.speed_mode = "realtime"
                print("🐌 SWITCHED TO REAL-TIME SPEED (6 seconds per round)")
            else:
                self.speed_mode = "fast"
                print("⚡ SWITCHED TO FAST SPEED (10 rounds per second)")
            return self.speed_mode
        self.speed_mode = "fast"  # "fast" or "realtime"
        self.speed_lock = threading.Lock()
        
    def load_data(self):
        """Load the 3-hour data file"""
        try:
            with open(self.data_file, 'r') as f:
                self.all_data = json.load(f)
            print(f"📁 Loaded {len(self.all_data)} rounds from {self.data_file}")
            return True
        except FileNotFoundError:
            print(f"❌ Data file {self.data_file} not found!")
            print("🔧 Run generate_3hour_data.py first to create the data file")
            return False
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def toggle_speed(self):
        """Toggle between fast and real-time speed"""
        with self.speed_lock:
            if self.speed_mode == "fast":
                self.speed_mode = "realtime"
                print("� SWITCHED TO REAL-TIME SPEED (6 seconds per round)")
            else:
                self.speed_mode = "fast"
                print("⚡ SWITCHED TO FAST SPEED (10 rounds per second)")
        return self.speed_mode
    
    def get_current_speed(self):
        """Get current speed mode"""
        return self.speed_mode
    
    def start_feed(self):
        """Start feeding data with speed control"""
        if not self.load_data():
            return False
        
        self.is_running = True
        
        def feed_process():
            print("🚀 STARTING FILE-BASED CASINO FEED WITH SPEED CONTROL")
            print("=" * 60)
            print("⚡ Starting in FAST mode - use Speed button to toggle")
            print("📡 Processing all 180 rounds with speed control...")
            
            for i in range(len(self.all_data)):
                if not self.is_running:
                    break
                
                payload = self.all_data[i]
                self.data_queue.put(payload)
                
                current_shoe = payload['payloadData']['shoe']
                outcome = payload['seats']['1']['first']['outcome']
                payout = payload['seats']['1']['first']['payout']
                
                # Get current speed
                with self.speed_lock:
                    current_speed = self.speed_mode
                
                # Speed-based delay
                if current_speed == "fast":
                    delay = 0.1  # 10 rounds per second
                    if i % 20 == 0:  # Progress updates for fast mode
                        progress = (i / len(self.all_data)) * 100
                        print(f"⚡ FAST: {progress:.0f}% - Round {i+1} ({current_shoe}) - {outcome}")
                else:
                    delay = 6  # 6 seconds per round
                    print(f"🐌 REAL-TIME: Round {i+1} ({current_shoe}) - {outcome} (${payout})")
                
                time.sleep(delay)
            
            print(f"\n🎉 FEED COMPLETE! Processed {len(self.all_data)} rounds")
        
        # Start in background thread
        thread = threading.Thread(target=feed_process, daemon=True)
        thread.start()
        return True
    
    def stop_feed(self):
        """Stop the data feed"""
        self.is_running = False
        print("🛑 File-based casino feed stopped")
    
    def get_status(self):
        """Get current feed status"""
        if not self.is_running:
            return "Stopped"
        elif not self.fast_forward_complete:
            return "Fast Forwarding"
        else:
            return "Real-Time Testing"

def main():
    """Test the file-based feed"""
    import queue
    
    # Test queue
    test_queue = queue.Queue()
    
    print("🧪 TESTING FILE-BASED CASINO FEED")
    print("=" * 50)
    
    feed = FileCasinoFeed(test_queue)
    
    if feed.load_data():
        print(f"✅ Ready to feed {len(feed.all_data)} rounds")
        print("📊 Phase 1: Fast forward 120 rounds (2 hours)")
        print("📊 Phase 2: Real-time 60 rounds (1 hour)")
        print("\n💡 Integration ready for tracker app!")
    else:
        print("❌ Please run generate_3hour_data.py first")

if __name__ == "__main__":
    main()
