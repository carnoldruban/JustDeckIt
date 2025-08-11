"""
Simulation Scraper - Reads from test data file instead of browser
"""

import json
import time
import threading
import queue

class Scraper:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.stop_event = threading.Event()
        self.is_running = False
        self.current_round = 0
        self.test_data = []
        self.feeder_thread = None
        self.load_test_data()
        
    def load_test_data(self):
        """Load test data from file"""
        try:
            with open("blackjack_test_data_300rounds.json", 'r') as f:
                self.test_data = json.load(f)
            self.log_status(f"Loaded {len(self.test_data)} rounds of test data")
        except FileNotFoundError:
            self.log_status("ERROR: Test data file not found! Please run generate_test_data.py first")
            self.test_data = []
        except Exception as e:
            self.log_status(f"ERROR loading test data: {e}")
            self.test_data = []

    def log_status(self, message):
        """Prints a status message to the console."""
        print(f"[SCRAPER SIM] {message}")
    
    def start(self):
        """Start the simulation scraper"""
        if not self.test_data:
            self.log_status("No test data available! Cannot start simulation.")
            return
            
        if self.is_running:
            self.log_status("Simulation already running!")
            return
            
        self.log_status("Starting simulation scraper...")
        self.stop_event.clear()
        self.is_running = True
        self.current_round = 0
        
        # Start feeding data in a separate thread
        self.feeder_thread = threading.Thread(target=self.feed_data_worker, daemon=True)
        self.feeder_thread.start()
    
    def stop(self):
        """Stop the simulation scraper"""
        self.log_status("Stopping simulation scraper...")
        self.stop_event.set()
        self.is_running = False
        
        if self.feeder_thread and self.feeder_thread.is_alive():
            self.feeder_thread.join(timeout=2.0)
    
    def feed_data_worker(self):
        """Worker thread that feeds test data to the queue round by round"""
        self.log_status(f"Starting data feed for {len(self.test_data)} rounds...")
        
        while self.is_running and not self.stop_event.is_set() and self.current_round < len(self.test_data):
            try:
                # Get current round data
                round_data = self.test_data[self.current_round]
                
                # Parse the serialized object
                payload_json = round_data.get("serialized_object", "{}")
                payload_data = json.loads(payload_json)
                
                # Extract the actual game data
                game_data = payload_data.get("payloadData", {})
                
                if game_data:
                    # Put data in queue for tracker app
                    self.data_queue.put(game_data)
                    self.log_status(f"Fed round {self.current_round + 1}/{len(self.test_data)} - Game ID: {game_data.get('gameId', 'Unknown')}")
                else:
                    self.log_status(f"Warning: No payload data in round {self.current_round + 1}")
                    
            except json.JSONDecodeError as e:
                self.log_status(f"Error parsing round {self.current_round + 1}: {e}")
            except Exception as e:
                self.log_status(f"Unexpected error in round {self.current_round + 1}: {e}")
            
            self.current_round += 1
            
            # Delay between rounds (simulate real-time play)
            # Fast mode: 0.5 seconds per round
            # Normal mode: 2-5 seconds per round
            delay = 1.0  # 1 second simulation mode
            
            # Check stop event with timeout
            if self.stop_event.wait(delay):
                break
        
        # Simulation complete
        if self.current_round >= len(self.test_data):
            self.log_status(f"Simulation complete! Processed {self.current_round} rounds")
        else:
            self.log_status("Simulation stopped by user")
        
        self.is_running = False
    
    def get_progress(self):
        """Get current simulation progress"""
        if not self.test_data:
            return 0, 0, 0.0
        
        total = len(self.test_data)
        current = self.current_round
        percentage = (current / total) * 100 if total > 0 else 0
        
        return current, total, percentage
    
    def is_simulation_complete(self):
        """Check if simulation is complete"""
        return self.current_round >= len(self.test_data) if self.test_data else True
    
    def restart_simulation(self):
        """Restart the simulation from the beginning"""
        self.stop()
        time.sleep(0.5)  # Brief pause
        self.current_round = 0
        self.start()

if __name__ == "__main__":
    # Test the scraper simulation
    test_queue = queue.Queue()
    scraper = Scraper(test_queue)
    
    print("Testing ScraperSim...")
    scraper.start()
    
    # Let it run for a few rounds
    time.sleep(5)
    
    # Check what data we got
    rounds_received = 0
    while not test_queue.empty():
        data = test_queue.get()
        rounds_received += 1
        if rounds_received <= 3:  # Show first 3 rounds
            print(f"Round {rounds_received}: Game ID {data.get('gameId', 'N/A')}")
    
    print(f"Total rounds received: {rounds_received}")
    scraper.stop()
