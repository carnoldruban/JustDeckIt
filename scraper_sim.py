import json
import time
import threading
import queue

class Scraper:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.stop_event = threading.Event()
        self.is_running = False
        self.test_data = []
        self.feeder_thread = None
        self._load_test_data()

    def _load_test_data(self):
        """Load test data from file"""
        try:
            with open("blackjack_test_data_300rounds.json", 'r') as f:
                self.test_data = json.load(f)
            self._log_status(f"Loaded {len(self.test_data)} rounds from test data.")
        except FileNotFoundError:
            self._log_status("ERROR: Test data file 'blackjack_test_data_300rounds.json' not found!")
            self.test_data = []
        except Exception as e:
            self._log_status(f"ERROR loading test data: {e}")
            self.test_data = []

    def _log_status(self, message):
        print(f"[SCRAPER SIM] {message}")

    def start(self):
        if not self.test_data:
            self._log_status("No test data available! Cannot start simulation.")
            return
        if self.is_running:
            self._log_status("Simulation already running!")
            return

        self._log_status("Starting simulation scraper...")
        self.stop_event.clear()
        self.is_running = True
        self.feeder_thread = threading.Thread(target=self._feed_data_worker, daemon=True)
        self.feeder_thread.start()

    def stop(self):
        self._log_status("Stopping simulation scraper...")
        self.stop_event.set()
        self.is_running = False
        if self.feeder_thread and self.feeder_thread.is_alive():
            self.feeder_thread.join(timeout=2.0)

    def _feed_data_worker(self):
        current_round = 0
        while self.is_running and not self.stop_event.is_set() and current_round < len(self.test_data):
            try:
                game_data = self.test_data[current_round]
                self.data_queue.put(game_data)
                self._log_status(f"Fed round {current_round + 1}/{len(self.test_data)}")
            except Exception as e:
                self._log_status(f"Error in round {current_round + 1}: {e}")

            current_round += 1
            delay = 0.1  # 100ms per round
            if self.stop_event.wait(delay):
                break

        if current_round >= len(self.test_data):
            self._log_status(f"Simulation complete! Processed {current_round} rounds.")
        else:
            self._log_status("Simulation stopped by user.")

        self.is_running = False
