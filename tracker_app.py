import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import threading
import json
import subprocess

# --- Module Imports ---
# Use the live scraper by default
from scraper import Scraper 
# For offline testing, comment the line above and uncomment the line below
# from scraper_sim import ScraperSim as Scraper 

from database_manager import DatabaseManager
from shoe_manager import ShoeManager
from card_counter import HiLoCounter, WongHalvesCounter
from strategy import get_strategy_action, get_bet_recommendation
from analytics_engine import AnalyticsEngine

class BlackjackTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack Tracker (DraftKings & OLG)")
        self.root.geometry("1200x700")

        self.db_manager = DatabaseManager()
        self.shoe_manager = ShoeManager(self.db_manager)
        self.analytics_engine = AnalyticsEngine(self.db_manager)
        
        self.hilo_counter = HiLoCounter()
        self.wong_halves_counter = WongHalvesCounter()
        
        self.scraper = None
        self.scraper_thread = None
        self.processed_cards = set()
        self.last_db_timestamp = None

        self.create_widgets()
        self.shoe_manager.set_active_shoe("Shoe 1")
        self.active_shoe_var.set("Shoe 1")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_ui_from_db()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)

        self.open_button = ttk.Button(top_frame, text="Open Browser", command=self.open_browser)
        self.open_button.pack(side=tk.LEFT, padx=5)

        self.track_button = ttk.Button(top_frame, text="Start Tracking", command=self.start_tracking)
        self.track_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(top_frame, text="Stop Tracking", command=self.stop_tracking, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        shoe_controls_frame = ttk.Frame(main_frame)
        shoe_controls_frame.pack(fill=tk.X, pady=5, anchor='w')

        ttk.Label(shoe_controls_frame, text="Active Shoe:").pack(side=tk.LEFT, padx=5)
        self.active_shoe_var = tk.StringVar()
        ttk.Label(shoe_controls_frame, textvariable=self.active_shoe_var, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # Add casino site display
        ttk.Label(shoe_controls_frame, text="| Casino:").pack(side=tk.LEFT, padx=5)
        self.casino_site_var = tk.StringVar(value="Not Connected")
        ttk.Label(shoe_controls_frame, textvariable=self.casino_site_var, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)

        self.end_shoe_button = ttk.Button(shoe_controls_frame, text="Mark End of Shoe / Switch & Shuffle", command=self.handle_shoe_end)
        self.end_shoe_button.pack(side=tk.LEFT, padx=10)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        live_tracker_tab = ttk.Frame(notebook, padding="10")
        shuffle_tracking_tab = ttk.Frame(notebook, padding="10")
        analytics_tab = ttk.Frame(notebook, padding="10")  # Add analytics tab

        notebook.add(live_tracker_tab, text="Live Tracker")
        notebook.add(shuffle_tracking_tab, text="Shoe & Shuffle Tracking")
        notebook.add(analytics_tab, text="Analytics & Predictions")  # Add analytics tab

        # Analytics tab content
        analytics_frame = ttk.Frame(analytics_tab, padding="10")
        analytics_frame.pack(fill=tk.BOTH, expand=True)
        
        # Performance Summary
        performance_frame = ttk.LabelFrame(analytics_frame, text="Performance Summary", padding="10")
        performance_frame.pack(fill=tk.X, pady=5)
        
        self.shoe_performance_var = tk.StringVar(value="Shoe Performance: Loading...")
        self.seat_performance_var = tk.StringVar(value="Seat Performance: Loading...")
        self.prediction_accuracy_var = tk.StringVar(value="Prediction Accuracy: Loading...")
        
        ttk.Label(performance_frame, textvariable=self.shoe_performance_var).pack(anchor="w")
        ttk.Label(performance_frame, textvariable=self.seat_performance_var).pack(anchor="w")
        ttk.Label(performance_frame, textvariable=self.prediction_accuracy_var).pack(anchor="w")
        
        # Decision Recommendations
        decision_frame = ttk.LabelFrame(analytics_frame, text="Decision Recommendations", padding="10")
        decision_frame.pack(fill=tk.X, pady=5)
        
        self.recommendation_var = tk.StringVar(value="Recommendation: Loading...")
        self.confidence_var = tk.StringVar(value="Confidence: Loading...")
        self.best_shoe_var = tk.StringVar(value="Best Shoe: Loading...")
        self.best_seat_var = tk.StringVar(value="Best Seat: Loading...")
        
        ttk.Label(decision_frame, textvariable=self.recommendation_var, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(decision_frame, textvariable=self.confidence_var).pack(anchor="w")
        ttk.Label(decision_frame, textvariable=self.best_shoe_var).pack(anchor="w")
        ttk.Label(decision_frame, textvariable=self.best_seat_var).pack(anchor="w")
        
        # Real-time Predictions
        predictions_frame = ttk.LabelFrame(analytics_frame, text="Next 5 Cards Prediction", padding="10")
        predictions_frame.pack(fill=tk.X, pady=5)
        
        self.predictions_var = tk.StringVar(value="Predictions: Loading...")
        ttk.Label(predictions_frame, textvariable=self.predictions_var, font=("Courier New", 12)).pack(anchor="w")

        live_left_frame = ttk.Frame(live_tracker_tab)
        live_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        live_right_frame = ttk.Frame(live_tracker_tab)
        live_right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        counting_frame = ttk.LabelFrame(live_left_frame, text="Card Counts", padding=10)
        counting_frame.pack(fill=tk.X, pady=5)
        self.hilo_rc_var = tk.StringVar(value="Hi-Lo RC: 0")
        self.hilo_tc_var = tk.StringVar(value="Hi-Lo TC: 0.00")
        self.wh_rc_var = tk.StringVar(value="Wong Halves RC: 0.0")
        self.wh_tc_var = tk.StringVar(value="Wong Halves TC: 0.00")
        ttk.Label(counting_frame, textvariable=self.hilo_rc_var).pack(side=tk.LEFT, padx=10)
        ttk.Label(counting_frame, textvariable=self.hilo_tc_var).pack(side=tk.LEFT, padx=10)
        ttk.Label(counting_frame, textvariable=self.wh_rc_var).pack(side=tk.LEFT, padx=10)
        ttk.Label(counting_frame, textvariable=self.wh_tc_var).pack(side=tk.LEFT, padx=10)

        strategy_frame = ttk.LabelFrame(live_left_frame, text="Strategy Assistant", padding=10)
        strategy_frame.pack(fill=tk.X, pady=5)
        ttk.Label(strategy_frame, text="My Seat (0-6):").pack(side=tk.LEFT, padx=5)
        self.seat_var = tk.StringVar(value="")
        ttk.Entry(strategy_frame, textvariable=self.seat_var, width=5).pack(side=tk.LEFT, padx=5)
        self.bet_rec_var = tk.StringVar(value="Bet: N/A")
        self.action_rec_var = tk.StringVar(value="Action: N/A")
        ttk.Label(strategy_frame, textvariable=self.bet_rec_var).pack(side=tk.LEFT, padx=10)
        ttk.Label(strategy_frame, textvariable=self.action_rec_var).pack(side=tk.LEFT, padx=10)

        ttk.Label(live_left_frame, text="Live Game Feed").pack(anchor="nw")
        self.display_area = scrolledtext.ScrolledText(live_left_frame, wrap=tk.WORD, state='disabled', font=("Courier New", 11))
        self.display_area.pack(fill=tk.BOTH, expand=True)

        self.zone_display_frame = ttk.LabelFrame(live_right_frame, text="Live Zone Analysis", padding=10)
        self.zone_display_frame.pack(fill=tk.Y, expand=True)

        self.cards_played_var = tk.StringVar(value="Cards Played: 0")
        ttk.Label(self.zone_display_frame, textvariable=self.cards_played_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=5, sticky='w', pady=5)

        headers = ["Zone", "Total", "Low %", "Mid %", "High %"]
        for col, header in enumerate(headers):
            ttk.Label(self.zone_display_frame, text=header, font=("Segoe UI", 9, "bold")).grid(row=1, column=col, padx=5)

        self.zone_labels = []
        for i in range(8):
            row_labels = {}
            row_labels['name'] = ttk.Label(self.zone_display_frame, text=f"Zone {i+1}")
            row_labels['name'].grid(row=i+2, column=0, padx=5, sticky='w')
            row_labels['total'] = ttk.Label(self.zone_display_frame, text="N/A")
            row_labels['total'].grid(row=i+2, column=1, padx=5)
            row_labels['low_pct'] = ttk.Label(self.zone_display_frame, text="N/A")
            row_labels['low_pct'].grid(row=i+2, column=2, padx=5)
            row_labels['mid_pct'] = ttk.Label(self.zone_display_frame, text="N/A")
            row_labels['mid_pct'].grid(row=i+2, column=3, padx=5)
            row_labels['high_pct'] = ttk.Label(self.zone_display_frame, text="N/A")
            row_labels['high_pct'].grid(row=i+2, column=4, padx=5)
            self.zone_labels.append(row_labels)

        shuffle_params_frame = ttk.LabelFrame(shuffle_tracking_tab, text="Shuffle Parameters", padding=10)
        shuffle_params_frame.pack(fill=tk.X, pady=10, anchor='n')

        ttk.Label(shuffle_params_frame, text="Number of Zones:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.zones_var = tk.StringVar(value="8")
        ttk.Entry(shuffle_params_frame, textvariable=self.zones_var, width=5).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(shuffle_params_frame, text="Number of Chunks:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.chunks_var = tk.StringVar(value="8")
        ttk.Entry(shuffle_params_frame, textvariable=self.chunks_var, width=5).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(shuffle_params_frame, text="Number of Iterations:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.iterations_var = tk.StringVar(value="4")
        ttk.Entry(shuffle_params_frame, textvariable=self.iterations_var, width=5).grid(row=2, column=1, sticky="w", padx=5, pady=2)

    def open_browser(self):
        bat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_chrome.bat")
        if os.path.exists(bat_file):
            subprocess.Popen([bat_file], creationflags=subprocess.CREATE_NEW_CONSOLE)

    def start_tracking(self):
        print("[UI] Starting tracking...")
        self.scraper = Scraper(self.db_manager, self.shoe_manager.active_shoe_name)
        
        # Start analytics session
        self.analytics_engine.start_session_tracking(self.shoe_manager.active_shoe_name)
        
        self.scraper_thread = threading.Thread(target=self.scraper.start, daemon=True)
        self.scraper_thread.start()
        
        # Update casino site display
        self.casino_site_var.set("Connecting...")
        
        self.track_button.config(state='disabled')
        self.stop_button.config(state='normal')

    def stop_tracking(self):
        if self.scraper:
            self.scraper.stop()
        
        # End analytics session
        self.analytics_engine.end_session_tracking()
        
        # Reset casino site display
        self.casino_site_var.set("Not Connected")
        
        self.track_button.config(state='normal')
        self.stop_button.config(state='disabled')

    def update_casino_site_display(self):
        """Updates the casino site display with current connection status."""
        if self.scraper:
            current_site = self.scraper.get_current_site()
            if current_site != "Not Connected":
                self.casino_site_var.set(current_site)

    def update_ui_from_db(self):
        latest_timestamp = self.db_manager.get_latest_timestamp(self.shoe_manager.active_shoe_name)
        
        if latest_timestamp != self.last_db_timestamp:
            print(f"[UI] DB change detected. Timestamp: {latest_timestamp}. Refreshing UI.")
            self.last_db_timestamp = latest_timestamp

            full_history = self.db_manager.get_round_history(self.shoe_manager.active_shoe_name, limit=50)
            self.display_area.configure(state='normal')
            self.display_area.delete('1.0', tk.END)
            for row in reversed(full_history):
                formatted_state = self.format_db_row(row)
                self.display_area.insert(tk.END, formatted_state + "\n")
            self.display_area.configure(state='disabled')
            
            _, dealt_cards_list = self.db_manager.get_shoe_cards(self.shoe_manager.active_shoe_name)
            new_cards = [card for card in dealt_cards_list if card not in self.processed_cards]
            if new_cards:
                print(f"[UI] Processing new cards for counters: {new_cards}")
                self.hilo_counter.process_cards(new_cards)
                self.wong_halves_counter.process_cards(new_cards)
                self.processed_cards.update(new_cards)
            self.update_counts_display()
            
            if full_history:
                self.update_strategy_display(full_history[0])
            self.update_zone_display()
            self.update_analytics_display()  # Add analytics update
            self.update_casino_site_display() # Update casino site display

        self.root.after(1000, self.update_ui_from_db)

    def format_db_row(self, row_tuple):
        parts = [f"Round {row_tuple[2]}:"]
        parts.append(f"D:{json.loads(row_tuple[3])}({row_tuple[4]})")
        for i in range(7):
            hand = json.loads(row_tuple[5 + i*3])
            if hand:
                score = row_tuple[6 + i*3]
                state = row_tuple[7 + i*3]
                parts.append(f"S{i}:{hand}({score},{state[0]})")
        return " | ".join(parts)

    def handle_shoe_end(self):
        try:
            shuffle_params = {"zones": int(self.zones_var.get()), "chunks": int(self.chunks_var.get()), "iterations": int(self.iterations_var.get())}
        except ValueError:
            messagebox.showerror("Invalid Shuffle Parameters", "Please enter valid integers.")
            return

        if self.shoe_manager.end_current_shoe_and_shuffle(shuffle_params):
            next_shoe = "Shoe 2" if self.shoe_manager.active_shoe_name == "Shoe 1" else "Shoe 1"
            self.shoe_manager.set_active_shoe(next_shoe)
            self.active_shoe_var.set(next_shoe)
            
            self.hilo_counter.reset()
            self.wong_halves_counter.reset()
            self.processed_cards.clear()
            
            self.display_area.configure(state='normal')
            self.display_area.delete('1.0', tk.END)
            self.update_game_display(f"--- Switched to {next_shoe}. Previous shoe is shuffling. ---\n")
            self.display_area.configure(state='disabled')
            self.update_zone_display()
        else:
            messagebox.showwarning("Shuffle In Progress", "A shuffle is already in progress.")

    def update_game_display(self, message):
        self.display_area.configure(state='normal')
        self.display_area.insert(tk.END, message)
        self.display_area.configure(state='disabled')
        self.display_area.see(tk.END)

    def update_zone_display(self):
        active_shoe = self.shoe_manager.get_active_shoe()
        if not active_shoe: return
        num_zones = int(self.zones_var.get())
        zone_info = active_shoe.get_zone_info(num_zones)
        cards_played = len(active_shoe.dealt_cards)
        self.cards_played_var.set(f"Cards Played: {cards_played}")

        last_dealt_card = self.shoe_manager.get_last_dealt_card()
        current_zone = active_shoe.get_card_zone(last_dealt_card, num_zones) if last_dealt_card else None

        for i, row_labels in enumerate(self.zone_labels):
            zone_name = f"Zone {i+1}"
            info = zone_info.get(zone_name)
            bg_color = "yellow" if (current_zone and current_zone == i + 1) else "#f0f0f0"
            if info:
                for label in row_labels.values(): label.config(background=bg_color)
                row_labels['name'].config(text=zone_name)
                row_labels['total'].config(text=str(info['total']))
                row_labels['low_pct'].config(text=f"{info['low_pct']:.1f}%")
                row_labels['mid_pct'].config(text=f"{info['mid_pct']:.1f}%")
                row_labels['high_pct'].config(text=f"{info['high_pct']:.1f}%")
            else:
                for label in row_labels.values(): label.config(text="--", background=bg_color)
    
    def update_counts_display(self):
        self.hilo_rc_var.set(f"Hi-Lo RC: {self.hilo_counter.get_running_count()}")
        self.hilo_tc_var.set(f"Hi-Lo TC: {self.hilo_counter.get_true_count():.2f}")
        self.wh_rc_var.set(f"Wong Halves RC: {self.wong_halves_counter.get_running_count():.1f}")
        self.wh_tc_var.set(f"Wong Halves TC: {self.wong_halves_counter.get_true_count():.2f}")

    def update_strategy_display(self, db_row):
        seat_num = self.seat_var.get()
        if not seat_num.isdigit():
            self.bet_rec_var.set("Bet: N/A")
            self.action_rec_var.set("Action: N/A")
            return

        true_count = self.hilo_counter.get_true_count()
        bet_rec = get_bet_recommendation(true_count)
        self.bet_rec_var.set(f"Bet: {bet_rec}")

        player_hand = json.loads(db_row[5 + int(seat_num) * 3])
        dealer_up_card = json.loads(db_row[3])[0] if json.loads(db_row[3]) else None

        if player_hand and dealer_up_card and dealer_up_card != '**':
            action_rec = get_strategy_action(player_hand, dealer_up_card, true_count)
            self.action_rec_var.set(f"Action: {action_rec}")
        else:
            self.action_rec_var.set("Action: N/A")

    def update_analytics_display(self):
        """Updates the analytics display with current data."""
        try:
            active_shoe = self.shoe_manager.get_active_shoe()
            if not active_shoe:
                return
            
            # Get shoe cards for predictions
            undealt_cards, dealt_cards = self.db_manager.get_shoe_cards(self.shoe_manager.active_shoe_name)
            
            # Update predictions
            predictions = self.analytics_engine.get_real_time_predictions(undealt_cards, dealt_cards)
            prediction_text = " ".join([f"[{p}]" for p in predictions])
            self.predictions_var.set(f"Next 5: {prediction_text}")
            
            # Update performance summary (placeholder data)
            self.shoe_performance_var.set("Shoe Performance: Active tracking...")
            self.seat_performance_var.set("Seat Performance: Collecting data...")
            self.prediction_accuracy_var.set("Prediction Accuracy: Calculating...")
            
            # Update recommendations
            true_count = self.hilo_counter.get_true_count()
            if true_count > 2:
                self.recommendation_var.set("🟢 RECOMMENDATION: FAVORABLE CONDITIONS")
                self.confidence_var.set("Confidence: High")
            elif true_count > 0:
                self.recommendation_var.set("🟡 RECOMMENDATION: MODERATE CONDITIONS")
                self.confidence_var.set("Confidence: Medium")
            else:
                self.recommendation_var.set("🔴 RECOMMENDATION: UNFAVORABLE CONDITIONS")
                self.confidence_var.set("Confidence: Low")
            
            self.best_shoe_var.set(f"Best Shoe: {self.shoe_manager.active_shoe_name}")
            self.best_seat_var.set("Best Seat: Analyzing...")
            
        except Exception as e:
            print(f"[Analytics] Error updating analytics: {e}")

    def on_closing(self):
        self.stop_tracking()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()