#!/usr/bin/env python3
"""
Comprehensive test runner for the Blackjack Tracker system.
Processes 1000 rounds of test data and monitors performance in detail.
"""

import json
import time
import threading
import tkinter as tk
from tkinter import ttk
import queue
from datetime import datetime
from logging_config import get_logger, log_performance, log_memory_usage

# Import all system components
from database_manager import DatabaseManager
from shoe_manager import ShoeManager
from card_counter import HiLoCounter, WongHalvesCounter
from strategy import get_strategy_action, get_bet_recommendation
from analytics_engine import AnalyticsEngine
from tracker_app import BlackjackTrackerApp

class ComprehensiveTestRunner:
    """Runs comprehensive tests on the entire blackjack tracker system."""
    
    def __init__(self):
        self.logger = get_logger("TestRunner")
        self.test_data = []
        self.results = {
            "rounds_processed": 0,
            "cards_processed": 0,
            "shoes_used": 0,
            "shuffles_performed": 0,
            "errors": [],
            "performance_metrics": {},
            "memory_usage": [],
            "start_time": None,
            "end_time": None
        }
        
        # Initialize system components
        self.db_manager = DatabaseManager("test_blackjack_data.db")
        self.shoe_manager = ShoeManager(self.db_manager)
        self.analytics_engine = AnalyticsEngine(self.db_manager)
        self.hilo_counter = HiLoCounter()
        self.wong_halves_counter = WongHalvesCounter()
        
        self.logger.info("ComprehensiveTestRunner initialized")
    
    @log_performance
    def load_test_data(self, filename="test_1000_rounds.json"):
        """Load test data from file."""
        self.logger.info("Loading test data from %s", filename)
        
        try:
            with open(filename, 'r') as f:
                self.test_data = json.load(f)
            
            self.logger.info("Loaded %d rounds of test data", len(self.test_data))
            return True
        except FileNotFoundError:
            self.logger.error("Test data file not found: %s", filename)
            return False
        except Exception as e:
            self.logger.error("Error loading test data: %s", e)
            return False
    
    @log_performance
    def process_round(self, round_data):
        """Process a single round of test data."""
        try:
            # Process with shoe manager
            dealt_cards = self.shoe_manager.process_game_state(round_data)
            
            if dealt_cards:
                # Update card counters
                card_ranks = [card[0] for card in dealt_cards]
                self.hilo_counter.process_cards(card_ranks)
                self.wong_halves_counter.process_cards(card_ranks)
                
                self.results["cards_processed"] += len(dealt_cards)
                
                # Log card processing
                self.logger.debug("Processed %d cards: %s", len(dealt_cards), card_ranks)
            
            # Update analytics
            if self.analytics_engine.current_session_id:
                # Track individual cards
                for i, card in enumerate(dealt_cards):
                    self.analytics_engine.track_card_dealt(
                        self.results["rounds_processed"],
                        str(card),
                        i + 1,
                        None,  # seat number
                        "player_card",
                        i + 1
                    )
            
            self.results["rounds_processed"] += 1
            
            # Check for shoe change (every ~50 rounds)
            if self.results["rounds_processed"] % 50 == 0:
                self.logger.info("Processed %d rounds, checking for shoe change", self.results["rounds_processed"])
                
                # Simulate shoe end and shuffle
                shuffle_params = {"zones": 8, "chunks": 8, "iterations": 4}
                if self.shoe_manager.end_current_shoe_and_shuffle(shuffle_params):
                    self.results["shoes_used"] += 1
                    self.results["shuffles_performed"] += 1
                    self.logger.info("Shoe change triggered, shuffle performed")
                    
                    # Switch to next shoe
                    next_shoe = "Shoe 2" if self.shoe_manager.active_shoe_name == "Shoe 1" else "Shoe 1"
                    self.shoe_manager.set_active_shoe(next_shoe)
                    
                    # Reset counters
                    self.hilo_counter.reset()
                    self.wong_halves_counter.reset()
            
            return True
            
        except Exception as e:
            self.logger.error("Error processing round %d: %s", self.results["rounds_processed"], e)
            self.results["errors"].append({
                "round": self.results["rounds_processed"],
                "error": str(e)
            })
            return False
    
    @log_performance
    def run_comprehensive_test(self):
        """Run the comprehensive test on all 1000 rounds."""
        self.logger.info("Starting comprehensive test with %d rounds", len(self.test_data))
        
        self.results["start_time"] = datetime.now()
        start_time = time.time()
        
        # Log initial memory usage
        initial_memory = log_memory_usage("TestRunner")
        self.results["memory_usage"].append({
            "round": 0,
            "memory_mb": initial_memory
        })
        
        successful_rounds = 0
        
        for i, round_data in enumerate(self.test_data):
            if self.process_round(round_data):
                successful_rounds += 1
            
            # Log progress every 100 rounds
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                current_memory = log_memory_usage("TestRunner")
                
                self.logger.info("Progress: %d/%d rounds (%.1f%%) in %.2f seconds", 
                               i + 1, len(self.test_data), 
                               (i + 1) / len(self.test_data) * 100, elapsed)
                
                self.logger.info("Performance: %.2f rounds/sec, Memory: %.2f MB", 
                               (i + 1) / elapsed, current_memory)
                
                # Record memory usage
                self.results["memory_usage"].append({
                    "round": i + 1,
                    "memory_mb": current_memory
                })
                
                # Log current counts
                self.logger.info("Current counts - Hi-Lo: %d (%.2f), Wong Halves: %.1f (%.2f)", 
                               self.hilo_counter.get_running_count(), self.hilo_counter.get_true_count(),
                               self.wong_halves_counter.get_running_count(), self.wong_halves_counter.get_true_count())
        
        self.results["end_time"] = datetime.now()
        total_time = time.time() - start_time
        
        # Final statistics
        self.results["performance_metrics"] = {
            "total_time_seconds": total_time,
            "rounds_per_second": len(self.test_data) / total_time,
            "successful_rounds": successful_rounds,
            "success_rate": successful_rounds / len(self.test_data) * 100,
            "final_memory_mb": log_memory_usage("TestRunner")
        }
        
        self.logger.info("Comprehensive test completed")
        self.logger.info("Results: %s", self.results["performance_metrics"])
        
        return self.results
    
    def generate_test_report(self):
        """Generate a detailed test report."""
        self.logger.info("Generating comprehensive test report")
        
        report = {
            "test_summary": {
                "test_date": datetime.now().isoformat(),
                "total_rounds": len(self.test_data),
                "successful_rounds": self.results["rounds_processed"],
                "success_rate": f"{self.results['rounds_processed'] / len(self.test_data) * 100:.2f}%"
            },
            "performance_metrics": self.results["performance_metrics"],
            "system_usage": {
                "shoes_used": self.results["shoes_used"],
                "shuffles_performed": self.results["shuffles_performed"],
                "cards_processed": self.results["cards_processed"],
                "memory_usage": self.results["memory_usage"]
            },
            "errors": self.results["errors"],
            "final_counts": {
                "hilo_running_count": self.hilo_counter.get_running_count(),
                "hilo_true_count": self.hilo_counter.get_true_count(),
                "wong_halves_running_count": self.wong_halves_counter.get_running_count(),
                "wong_halves_true_count": self.wong_halves_counter.get_true_count()
            }
        }
        
        # Save report to file
        report_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info("Test report saved to %s", report_filename)
        return report
    
    def run_gui_test(self):
        """Run a GUI-based test with real-time monitoring."""
        self.logger.info("Starting GUI-based test")
        
        # Create test GUI
        root = tk.Tk()
        root.title("Comprehensive Test Runner")
        root.geometry("800x600")
        
        # Create GUI components
        self.create_test_gui(root)
        
        # Start test in background thread
        test_thread = threading.Thread(target=self.run_background_test, daemon=True)
        test_thread.start()
        
        # Start GUI update loop
        self.update_gui()
        
        root.mainloop()
    
    def create_test_gui(self, root):
        """Create the test GUI components."""
        # Progress frame
        progress_frame = ttk.LabelFrame(root, text="Test Progress", padding="10")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress_var = tk.StringVar(value="Ready to start test")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(root, text="Real-time Statistics", padding="10")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create text widget for statistics
        self.stats_text = tk.Text(stats_frame, height=20, width=80)
        scrollbar = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=scrollbar.set)
        
        self.stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Control frame
        control_frame = ttk.Frame(root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_button = ttk.Button(control_frame, text="Start Test", command=self.start_gui_test)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Test", command=self.stop_gui_test, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
    
    def start_gui_test(self):
        """Start the GUI-based test."""
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Load test data if not already loaded
        if not self.test_data:
            if not self.load_test_data():
                self.progress_var.set("Error: Could not load test data")
                return
        
        self.progress_var.set("Test started")
        self.test_running = True
    
    def stop_gui_test(self):
        """Stop the GUI-based test."""
        self.test_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_var.set("Test stopped")
    
    def run_background_test(self):
        """Run the test in the background thread."""
        if not self.test_data:
            return
        
        for i, round_data in enumerate(self.test_data):
            if not self.test_running:
                break
            
            self.process_round(round_data)
            
            # Update progress
            progress = (i + 1) / len(self.test_data) * 100
            self.progress_var.set(f"Processing round {i + 1}/{len(self.test_data)} ({progress:.1f}%)")
            
            # Small delay to allow GUI updates
            time.sleep(0.01)
        
        self.progress_var.set("Test completed")
        self.test_running = False
    
    def update_gui(self):
        """Update the GUI with current statistics."""
        if hasattr(self, 'stats_text'):
            # Clear and update statistics
            self.stats_text.delete(1.0, tk.END)
            
            stats = f"""
=== COMPREHENSIVE TEST STATISTICS ===

Rounds Processed: {self.results['rounds_processed']}/{len(self.test_data)}
Cards Processed: {self.results['cards_processed']}
Shoes Used: {self.results['shoes_used']}
Shuffles Performed: {self.results['shuffles_performed']}

Current Counts:
- Hi-Lo Running Count: {self.hilo_counter.get_running_count()}
- Hi-Lo True Count: {self.hilo_counter.get_true_count():.2f}
- Wong Halves Running Count: {self.wong_halves_counter.get_running_count():.1f}
- Wong Halves True Count: {self.wong_halves_counter.get_true_count():.2f}

Active Shoe: {self.shoe_manager.active_shoe_name}
Cards in Current Shoe: {len(self.shoe_manager.get_active_shoe().undealt_cards) if self.shoe_manager.get_active_shoe() else 0}

Errors: {len(self.results['errors'])}
"""
            
            self.stats_text.insert(tk.END, stats)
        
        # Schedule next update
        if hasattr(self, 'test_running') and self.test_running:
            threading.Timer(1.0, self.update_gui).start()

def main():
    """Run the comprehensive test."""
    runner = ComprehensiveTestRunner()
    
    # Load test data
    if not runner.load_test_data():
        print("Error: Could not load test data. Run test_data_generator.py first.")
        return
    
    # Run test
    results = runner.run_comprehensive_test()
    
    # Generate report
    report = runner.generate_test_report()
    
    print("\n=== COMPREHENSIVE TEST COMPLETED ===")
    print(f"Rounds processed: {results['rounds_processed']}")
    print(f"Success rate: {results['performance_metrics']['success_rate']:.2f}%")
    print(f"Performance: {results['performance_metrics']['rounds_per_second']:.2f} rounds/sec")
    print(f"Total time: {results['performance_metrics']['total_time_seconds']:.2f} seconds")
    print(f"Final memory usage: {results['performance_metrics']['final_memory_mb']:.2f} MB")

if __name__ == "__main__":
    main()



