import json
import time
import asyncio
from datetime import datetime
from database_manager import DatabaseManager
from logging_config import get_logger

class ScraperSimulator:
    """Simulates the scraper by reading from test data files instead of WebSocket"""
    
    def __init__(self, db_manager, shoe_name, shoe_manager=None, test_file="test_game_data.json"):
        self.db_manager = db_manager
        self.shoe_name = shoe_name
        self.shoe_manager = shoe_manager
        self.test_file = test_file
        self.logger = get_logger("ScraperSim")
        self.running = False
        self.current_index = 0
        self.test_data = []
        
    def load_test_data(self):
        """Load test data from JSON file"""
        try:
            with open(self.test_file, 'r') as f:
                self.test_data = json.load(f)
            self.logger.info(f"Loaded {len(self.test_data)} test game events from {self.test_file}")
            return True
        except FileNotFoundError:
            self.logger.error(f"Test file {self.test_file} not found")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing test file: {e}")
            return False
    
    def start_simulation(self, delay_between_events=2.0):
        """Start the simulation with specified delay between events"""
        if not self.load_test_data():
            return False
            
        self.running = True
        self.current_index = 0
        self.logger.info(f"Starting scraper simulation with {len(self.test_data)} events")
        
        # Run simulation in a separate thread to avoid blocking
        import threading
        self.simulation_thread = threading.Thread(target=self._run_simulation, args=(delay_between_events,))
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        return True
    
    def _run_simulation(self, delay):
        """Internal method to run the simulation loop"""
        while self.running and self.current_index < len(self.test_data):
            try:
                # Get current event
                event = self.test_data[self.current_index]
                
                # Process the event
                self._process_game_event(event)
                
                # Move to next event
                self.current_index += 1
                
                # Wait before next event
                if self.current_index < len(self.test_data):
                    time.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"Error processing event {self.current_index}: {e}")
                self.current_index += 1
        
        if self.current_index >= len(self.test_data):
            self.logger.info("Simulation completed - all events processed")
        
        self.running = False
    
    def _process_game_event(self, event):
        """Process a single game event (similar to scraper's process_message)"""
        try:
            # Log the event processing
            self.logger.info(f"Processing event: Round {event.get('round_number', 'N/A')}, Phase: {event.get('phase', 'N/A')}")
            
            # Create payload in the format expected by database_manager
            payload = {
                'timestamp': event.get('timestamp', datetime.now().isoformat()),
                'game_id': event.get('game_id', 'unknown'),
                'shoe_name': event.get('shoe_name', self.shoe_name),
                'round_number': event.get('round_number', 0),
                'phase': event.get('phase', 'unknown'),
                'dealer_cards': event.get('dealer_cards', []),
                'player_hands': event.get('player_hands', []),
                'deck_info': event.get('deck_info', {})
            }
            
            # Log to database (same as real scraper)
            if self.db_manager:
                self.db_manager.log_round_update(payload)
            
            # Process with shoe manager if available (same as real scraper)
            if self.shoe_manager:
                self.shoe_manager.process_game_state(payload)
                
            # Log card details for debugging
            all_cards = payload['dealer_cards'].copy()
            for hand in payload['player_hands']:
                all_cards.extend(hand.get('cards', []))
            
            if all_cards:
                self.logger.debug(f"Cards in this event: {', '.join(all_cards)}")
                
        except Exception as e:
            self.logger.error(f"Error processing game event: {e}")
            self.logger.error(f"Event data: {event}")
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.running = False
        self.logger.info("Simulation stopped")
    
    def get_simulation_status(self):
        """Get current simulation status"""
        return {
            'running': self.running,
            'current_event': self.current_index,
            'total_events': len(self.test_data),
            'progress_percent': (self.current_index / len(self.test_data) * 100) if self.test_data else 0
        }
    
    def reset_simulation(self):
        """Reset simulation to beginning"""
        self.current_index = 0
        self.logger.info("Simulation reset to beginning")

# For compatibility with tracker_app.py, provide the same interface as Scraper
class Scraper(ScraperSimulator):
    """Compatibility wrapper to match the original Scraper interface"""
    
    def __init__(self, db_manager, shoe_name, shoe_manager=None):
        super().__init__(db_manager, shoe_name, shoe_manager)
        self.logger.info("Scraper initialized in simulation mode")
    
    def start(self):
        """Start method to match original scraper interface"""
        self.logger.info("Starting scraper in simulation mode")
        return self.start_simulation(delay_between_events=1.5)  # Faster for testing
    
    def stop(self):
        """Stop method to match original scraper interface"""
        self.stop_simulation()

if __name__ == "__main__":
    # Test the simulator independently
    from database_manager import DatabaseManager
    
    # Initialize components
    db_manager = DatabaseManager()
    simulator = ScraperSimulator(db_manager, "Shoe A")
    
    # Run simulation
    print("Starting simulation test...")
    if simulator.start_simulation(delay_between_events=1.0):
        # Let it run for a bit
        time.sleep(10)
        
        # Check status
        status = simulator.get_simulation_status()
        print(f"Simulation status: {status}")
        
        # Stop simulation
        simulator.stop_simulation()
        print("Simulation test completed")
    else:
        print("Failed to start simulation")
