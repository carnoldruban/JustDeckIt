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

        # Progressive simulation scraper
        class Scraper:
            def __init__(self, data_queue):
                self.data_queue = data_queue
                self.stop_event = threading.Event()
                self.is_running = False
                self.current_msg = 0
                self.test_data = []
                self.feeder_thread = None
                self.load_test_data()

            def load_test_data(self):
                """Load progressive test data from file"""
                try:
                    with open("blackjack_progressive_test_data.json", 'r') as f:
                        self.test_data = json.load(f)
                    self.log_status(f"Loaded {len(self.test_data)} progressive messages")
                except FileNotFoundError:
                    self.log_status("ERROR: Progressive test data file not found! Please run generate_progressive_test_data.py first")
                    self.test_data = []
                except Exception as e:
                    self.log_status(f"ERROR loading progressive test data: {e}")
                    self.test_data = []

            def log_status(self, message):
                print(f"[SCRAPER SIM] {message}")

            def start(self):
                if not self.test_data:
                    self.log_status("No progressive test data available! Cannot start simulation.")
                    return
                if self.is_running:
                    self.log_status("Simulation already running!")
                    return
                self.log_status("Starting progressive simulation scraper...")
                self.stop_event.clear()
                self.is_running = True
                self.current_msg = 0
                self.feeder_thread = threading.Thread(target=self.feed_data_worker, daemon=True)
                self.feeder_thread.start()

            def stop(self):
                self.log_status("Stopping progressive simulation scraper...")
                self.stop_event.set()
                self.is_running = False
                if self.feeder_thread and self.feeder_thread.is_alive():
                    self.feeder_thread.join(timeout=2.0)

            def feed_data_worker(self):
                self.log_status(f"Starting progressive data feed for {len(self.test_data)} messages...")
                while self.is_running and not self.stop_event.is_set() and self.current_msg < len(self.test_data):
                    try:
                        msg = self.test_data[self.current_msg]
                        payload_json = msg.get("serialized_object", "{}")
                        payload_data = json.loads(payload_json)
                        game_data = payload_data.get("payloadData", {})
                        if game_data:
                            self.data_queue.put(game_data)
                            self.log_status(f"Fed message {self.current_msg + 1}/{len(self.test_data)} - Game ID: {game_data.get('gameId', 'Unknown')}")
                        else:
                            self.log_status(f"Warning: No payload data in message {self.current_msg + 1}")
                    except Exception as e:
                        self.log_status(f"Error in message {self.current_msg + 1}: {e}")
                    self.current_msg += 1
                    delay = 0.7  # 700ms per message for realism
                    if self.stop_event.wait(delay):
                        break
                if self.current_msg >= len(self.test_data):
                    self.log_status(f"Simulation complete! Processed {self.current_msg} messages")
                else:
                    self.log_status("Simulation stopped by user")
                self.is_running = False

            def get_progress(self):
                if not self.test_data:
                    return 0, 0, 0.0
                total = len(self.test_data)
                current_msg = self.current_msg
                percentage = (current_msg / total) * 100 if total > 0 else 0
                return current_msg, total, percentage

            def is_simulation_complete(self):
                return self.current_msg >= len(self.test_data) if self.test_data else True

            def restart_simulation(self):
                self.stop()
                time.sleep(0.5)
                self.current_msg = 0
                self.start()

        if __name__ == "__main__":
            test_queue = queue.Queue()
            scraper = Scraper(test_queue)
            print("Testing Progressive ScraperSim...")
            scraper.start()
            time.sleep(5)
            msgs_received = 0
            while not test_queue.empty():
                data = test_queue.get()
                msgs_received += 1
                if msgs_received <= 3:
                    print(f"Msg {msgs_received}: Game ID {data.get('gameId', 'N/A')}")
            print(f"Total messages received: {msgs_received}")
            scraper.stop()
        return current, total, percentage
