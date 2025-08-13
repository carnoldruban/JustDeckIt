import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import os
import threading
import queue
import json
from scraper import Scraper
from card_counter import CardCounter
from database_manager import DBManager
from shoe_manager import ShoeManager
from predictor import SequencePredictor
from analytics_engine import AnalyticsEngine
from prediction_validator import PredictionValidator
from strategy import get_strategy_action, get_bet_recommendation

class BlackjackTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack Tracker & Predictor")
        self.root.geometry("800x700")
        self.root.configure(bg="#FFFACD")

        self.scraper = None
        self.scraper_thread = None
        self.data_queue = queue.Queue()
        self.card_counter = CardCounter(num_decks=8)
        self.db_manager = DBManager()
        self.shoe_manager = ShoeManager()
        self.predictor = SequencePredictor()
        self.analytics_engine = AnalyticsEngine(self.db_manager)
        self.prediction_validator = PredictionValidator(self.analytics_engine)

        self.is_tracking = False
        self.player_hand = []
        self.dealer_hand = []

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.setup_styles()

        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.live_tracker_tab = ttk.Frame(self.notebook)
        self.shoe_tracking_tab = ttk.Frame(self.notebook)
        self.analytics_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.live_tracker_tab, text="Live Tracker")
        self.notebook.add(self.shoe_tracking_tab, text="Shoe Tracking")
        self.notebook.add(self.analytics_tab, text="Analytics & Predictions")

        self.create_live_tracker_tab()
        self.create_shoe_tracking_tab()
        self.create_analytics_tab(self.analytics_tab)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queues()

    def setup_styles(self):
        # Placeholder for style configurations
        pass

    def create_live_tracker_tab(self):
        # Top frame
        top_frame = ttk.Frame(self.live_tracker_tab)
        top_frame.pack(fill=tk.X, pady=5)
        ttk.Label(top_frame, text="Game URL:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar(value="https://casino.draftkings.com")
        ttk.Entry(top_frame, textvariable=self.url_var, width=40).pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.open_button = ttk.Button(top_frame, text="Open Browser", command=self.open_browser)
        self.open_button.pack(side=tk.LEFT, padx=5)
        self.track_button = ttk.Button(top_frame, text="Start Tracking", command=self.start_tracking)
        self.track_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(top_frame, text="Stop Tracking", command=self.stop_tracking, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Counts Frame
        counts_frame = ttk.Frame(self.live_tracker_tab)
        counts_frame.pack(fill=tk.X, pady=5)
        self.running_count_label = ttk.Label(counts_frame, text="Running Count: 0", font=("Arial", 14, "bold"))
        self.running_count_label.pack(side=tk.LEFT, padx=10)
        self.true_count_label = ttk.Label(counts_frame, text="True Count: 0.00", font=("Arial", 14, "bold"))
        self.true_count_label.pack(side=tk.LEFT, padx=10)

        # Strategy Frame
        strategy_frame = ttk.LabelFrame(self.live_tracker_tab, text="Strategy Assistant", padding="10")
        strategy_frame.pack(fill=tk.X, padx=10, pady=10)
        self.bet_recommendation_label = ttk.Label(strategy_frame, text="Recommended Bet: -", font=("Arial", 12, "bold"))
        self.bet_recommendation_label.pack(side=tk.LEFT, padx=10)
        self.strategy_action_label = ttk.Label(strategy_frame, text="Recommended Action: -", font=("Arial", 12, "bold"))
        self.strategy_action_label.pack(side=tk.LEFT, padx=10)

        # Predictions Frame (Restored)
        predictions_frame = ttk.LabelFrame(self.live_tracker_tab, text="Predictions", padding="10")
        predictions_frame.pack(fill=tk.X, padx=10, pady=10)
        self.prediction_label = ttk.Label(predictions_frame, text="Prediction: -")
        self.prediction_label.pack()

        # Zone Analysis Frame (Restored)
        zone_analysis_frame = ttk.LabelFrame(self.live_tracker_tab, text="Zone Analysis", padding="10")
        zone_analysis_frame.pack(fill=tk.X, padx=10, pady=5)
        self.zone_analysis_label = ttk.Label(zone_analysis_frame, text="Zone analysis: -")
        self.zone_analysis_label.pack()

        # Display Area
        self.display_area = scrolledtext.ScrolledText(self.live_tracker_tab, wrap=tk.WORD, state='disabled')
        self.display_area.pack(fill=tk.BOTH, expand=True)

    def create_shoe_tracking_tab(self):
        # Placeholder content for Shoe Tracking tab (Restored)
        ttk.Label(self.shoe_tracking_tab, text="Shoe tracking controls will be here.").pack(pady=20)

    def open_browser(self):
        url = self.url_var.get()
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
        if os.path.exists(chrome_path):
            subprocess.Popen([chrome_path, url, "--remote-debugging-port=9222"])
        else:
            self.log_to_display("Chrome not found. Please open manually with --remote-debugging-port=9222")

    def start_tracking(self):
        self.scraper = Scraper(self.data_queue)
        self.scraper_thread = threading.Thread(target=self.scraper.start, daemon=True)
        self.scraper_thread.start()
        self.track_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.is_tracking = True

    def stop_tracking(self):
        if self.scraper: self.scraper.stop()
        if self.scraper_thread: self.scraper_thread.join(timeout=2)
        self.track_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.is_tracking = False

    def process_queues(self):
        try:
            while not self.data_queue.empty():
                message = self.data_queue.get_nowait()
                try:
                    data = json.loads(message)
                    dealt_cards = data.get('dealtCards', [])
                    self.player_hand = data.get('playerHand', [])
                    self.dealer_hand = data.get('dealerHand', [])

                    if dealt_cards:
                        self.card_counter.update_count(dealt_cards)

                    true_count = self.card_counter.get_true_count()
                    self.running_count_label.config(text=f"Running Count: {self.card_counter.get_running_count()}")
                    self.true_count_label.config(text=f"True Count: {true_count:.2f}")

                    # Update strategy UI
                    bet_rec = get_bet_recommendation(true_count)
                    self.bet_recommendation_label.config(text=f"Recommended Bet: {bet_rec} unit(s)")
                    if self.player_hand and self.dealer_hand:
                        action_rec = get_strategy_action(self.player_hand, self.dealer_hand[0], true_count)
                        self.strategy_action_label.config(text=f"Recommended Action: {action_rec}")

                    # (Placeholder for updating restored UI)
                    # self.prediction_label.config(text=f"Prediction: {self.predictor.get_prediction( ... )}")
                    # self.zone_analysis_label.config(text=f"Zone: {self.analytics_engine.get_zone_info( ... )}")

                except Exception as e:
                    self.log_to_display(f"Error: {e}")
        finally:
            self.root.after(100, self.process_queues)

    def log_to_display(self, message):
        self.display_area.config(state='normal')
        self.display_area.insert(tk.END, str(message) + '\n')
        self.display_area.config(state='disabled')
        self.display_area.see(tk.END)

    def create_analytics_tab(self, tab):
        ttk.Label(tab, text="Analytics will be displayed here.").pack(pady=20)

    def on_closing(self):
        if self.is_tracking:
            self.stop_tracking()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
