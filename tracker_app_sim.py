import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import os
import threading
import queue
import json
from scraper_sim import Scraper  # Use simulation scraper
from card_counter import CardCounter
from database_manager_sim import DBManager  # Use simulation database manager
from shoe_manager import ShoeManager
from predictor import SequencePredictor
from analytics_engine import AnalyticsEngine
from prediction_validator import PredictionValidator

class BlackjackTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack Tracker & Predictor")
        self.root.geometry("800x700")
        self.root.configure(bg="#FFFACD")  # LemonChiffon

        self.scraper = None
        self.scraper_thread = None
        self.data_queue = queue.Queue()
        self.card_counter = CardCounter(num_decks=8)
        self.db_manager = DBManager()
        self.shoe_manager = ShoeManager(default_regions=8)
        self.predictor = SequencePredictor()
        self.analytics_engine = AnalyticsEngine(self.db_manager)
        self.prediction_validator = PredictionValidator(self.analytics_engine)

        # UI State
        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None
        self.current_dealing_position = 0
        self.current_session_id = None
        self.is_tracking = False
        self.current_shoe = "None"

        # --- Style configuration ---
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Colors
        BG_COLOR = "#FFFACD"      # LemonChiffon
        FRAME_BG_COLOR = "#FFFFF0" # Ivory
        BUTTON_BG = "#FFFFFF"     # White
        BUTTON_ACTIVE_BG = "#F0F0F0"
        TEXT_COLOR = "#333333"

        # Fonts
        FONT_FAMILY = "Segoe UI"
        FONT_NORMAL = (FONT_FAMILY, 10)
        FONT_BOLD = (FONT_FAMILY, 10, "bold")
        FONT_HEADER = (FONT_FAMILY, 12, "bold")
        FONT_MONO = ("Courier New", 10)

        self.style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR, font=FONT_NORMAL)
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("TLabel", background=BG_COLOR, font=FONT_NORMAL)
        self.style.configure("TLabelFrame", background=BG_COLOR, font=FONT_BOLD)
        self.style.configure("TLabelFrame.Label", background=BG_COLOR, font=FONT_BOLD)

        self.style.configure("TButton",
                             background=BUTTON_BG,
                             foreground=TEXT_COLOR,
                             font=FONT_BOLD,
                             borderwidth=1,
                             relief="solid",
                             padding=6)
        self.style.map("TButton",
                       background=[('active', BUTTON_ACTIVE_BG)])

        # Main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create Tabbed Interface
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.live_tracker_tab = ttk.Frame(self.notebook)
        self.shoe_tracking_tab = ttk.Frame(self.notebook)
        self.analytics_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.live_tracker_tab, text="Live Tracker")
        self.notebook.add(self.shoe_tracking_tab, text="Shoe Tracking")
        self.notebook.add(self.analytics_tab, text="Analytics & Predictions")

        # Initialize live demo monitoring
        self.live_demo_active = False
        self.live_demo_data = {}
        
        # Start live demo monitor after everything is initialized
        self.root.after(1000, self.start_live_demo_monitor)

        # --- Live Tracker Tab Content ---
        # Top frame for URL and buttons
        self.top_frame = ttk.Frame(self.live_tracker_tab)
        self.top_frame.pack(fill=tk.X, pady=5)

        # URL Input
        self.url_label = ttk.Label(self.top_frame, text="Game URL:")
        self.url_label.pack(side=tk.LEFT, padx=(0, 5))

        self.url_var = tk.StringVar(value="https://casino.draftkings.com")
        self.url_entry = ttk.Entry(self.top_frame, textvariable=self.url_var, width=40, font=("Arial", 12))
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Control Buttons
        self.open_button = ttk.Button(self.top_frame, text="Open Browser", command=self.open_browser)
        self.open_button.pack(side=tk.LEFT, padx=5)

        self.track_button = ttk.Button(self.top_frame, text="Start Tracking", command=self.start_tracking)
        self.track_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(self.top_frame, text="Stop Tracking", command=self.stop_tracking, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Shoe Controls Frame
        self.shoe_controls_frame = ttk.Frame(self.live_tracker_tab)
        self.shoe_controls_frame.pack(fill=tk.X, pady=5)

        self.shoe_select_label = ttk.Label(self.shoe_controls_frame, text="Active Shoe:")
        self.shoe_select_label.pack(side=tk.LEFT, padx=(0, 5))

        self.shoe_var = tk.StringVar(value="Shoe 1")
        self.shoe_select_menu = ttk.OptionMenu(self.shoe_controls_frame, self.shoe_var, "Shoe 1", "Shoe 1", "Shoe 2", command=self.on_shoe_select)
        self.shoe_select_menu.pack(side=tk.LEFT, padx=5)

        self.end_shoe_button = ttk.Button(self.shoe_controls_frame, text="Mark End of Shoe", command=self.mark_end_of_shoe)
        self.end_shoe_button.pack(side=tk.LEFT, padx=5)

        # Counts Frame
        self.counts_frame = ttk.Frame(self.live_tracker_tab)
        self.counts_frame.pack(fill=tk.X, pady=5)

        self.running_count_label = ttk.Label(self.counts_frame, text="Running Count: 0", font=("Arial", 14, "bold"))
        self.running_count_label.pack(side=tk.LEFT, padx=10)

        self.true_count_label = ttk.Label(self.counts_frame, text="True Count: 0.00", font=("Arial", 14, "bold"))
        self.true_count_label.pack(side=tk.LEFT, padx=10)

        self.cards_played_label = ttk.Label(self.counts_frame, text="Cards Played: 0", font=("Arial", 14, "bold"))
        self.cards_played_label.pack(side=tk.LEFT, padx=10)

        self.decks_remaining_label = ttk.Label(self.counts_frame, text="Decks Left: 8.0", font=("Arial", 14, "bold"))
        self.decks_remaining_label.pack(side=tk.LEFT, padx=10)

        # Predictions Frame
        self.predictions_frame = ttk.LabelFrame(self.live_tracker_tab, text="Predictions", padding="10")
        self.predictions_frame.pack(fill=tk.X, padx=10, pady=10)

        self.prediction_label = ttk.Label(self.predictions_frame, text="Next 10-Val Window: [ ? | ? | ? | <10> | ? | ? | ? ]", font=("Courier New", 12, "bold"))
        self.prediction_label.pack(pady=(0, 5))

        self.sequence_prediction_label = ttk.Label(self.predictions_frame, text="Sequence Prediction: Analyzing...", font=("Courier New", 12, "bold"), foreground="blue")
        self.sequence_prediction_label.pack(pady=(0, 5))

        # Enhanced Card Range Predictions
        self.card_range_frame = ttk.Frame(self.predictions_frame)
        self.card_range_frame.pack(fill=tk.X, pady=5)

        ttk.Label(self.card_range_frame, text="Next 5 Cards:", font=("Arial", 11, "bold")).pack(side=tk.LEFT)

        self.card_range_labels = []
        for i in range(5):
            label = ttk.Label(self.card_range_frame, text="?", font=("Arial", 12, "bold"), 
                            foreground="gray", background="white", relief="solid", width=6)
            label.pack(side=tk.LEFT, padx=2)
            self.card_range_labels.append(label)

        # Prediction Accuracy Display
        self.accuracy_frame = ttk.Frame(self.predictions_frame)
        self.accuracy_frame.pack(fill=tk.X, pady=5)

        self.prediction_accuracy_label = ttk.Label(self.accuracy_frame, text="Prediction Accuracy: Calculating...", 
                                                  font=("Arial", 10), foreground="green")
        self.prediction_accuracy_label.pack(side=tk.LEFT)

        # Zone Analysis Frame
        self.zone_analysis_frame = ttk.LabelFrame(self.live_tracker_tab, text="Zone Analysis", padding="10")
        self.zone_analysis_frame.pack(fill=tk.X, padx=10, pady=5)

        self.zone_analysis_label = ttk.Label(self.zone_analysis_frame, text="Zone analysis requires a tracked shoe.", justify=tk.LEFT, font=FONT_MONO)
        self.zone_analysis_label.pack()


        # Display Area
        self.display_label = ttk.Label(self.live_tracker_tab, text="Live Game Feed")
        self.display_label.pack(fill=tk.X, pady=(10, 2))

        self.display_area = scrolledtext.ScrolledText(self.live_tracker_tab, wrap=tk.WORD, font=("Courier New", 11), state='disabled')
        self.display_area.pack(fill=tk.BOTH, expand=True)

        # --- Shoe Tracking Tab Content ---
        self.shuffle_form_frame = ttk.LabelFrame(self.shoe_tracking_tab, text="Shuffle Configuration", padding="10")
        self.shuffle_form_frame.pack(fill=tk.X, padx=10, pady=10)

        # Simple form for now, will be expanded
        self.regions_label = ttk.Label(self.shuffle_form_frame, text="Number of Regions:")
        self.regions_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        self.regions_var = tk.StringVar(value="4")
        self.regions_entry = ttk.Entry(self.shuffle_form_frame, textvariable=self.regions_var, width=10)
        self.regions_entry.grid(row=0, column=1, sticky=tk.W, pady=2)

        self.riffles_label = ttk.Label(self.shuffle_form_frame, text="Number of Riffles:")
        self.riffles_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.riffles_var = tk.StringVar(value="7")
        self.riffles_entry = ttk.Entry(self.shuffle_form_frame, textvariable=self.riffles_var, width=10)
        self.riffles_entry.grid(row=1, column=1, sticky=tk.W, pady=2)

        self.shuffle_button = ttk.Button(self.shoe_tracking_tab, text="Perform Shuffle", command=self.perform_shuffle)
        self.shuffle_button.pack(pady=10)

        # --- Analytics Tab Content ---
        self.create_analytics_tab(self.analytics_tab)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queues()

    def open_browser(self):
        bat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_chrome.bat")
        if os.path.exists(bat_file):
            print(f"[UI] Executing {bat_file}...")
            try:
                url = self.url_var.get()
                if not url:
                    print("[UI] Error: URL field cannot be empty.")
                    return
                print(f"[UI] Attempting to launch Chrome at: {url}")
                subprocess.Popen([bat_file, url], creationflags=subprocess.CREATE_NEW_CONSOLE)
                print("[UI] Browser launch script started. Please log in and navigate to the game page.")
            except Exception as e:
                print(f"[UI] Error executing .bat file: {e}")
        else:
            print("[UI] Error: restart_chrome.bat not found.")

    def toggle_speed(self):
        """Toggle feed speed between fast and real-time"""
        if hasattr(self, 'casino_feed') and self.casino_feed:
            new_speed = self.casino_feed.toggle_speed()
            
            # Update button text based on current speed
            if new_speed == "fast":
                self.speed_button.config(text="Speed: Fast ⚡")
                # Update display
                self.display_area.configure(state='normal')
                self.display_area.insert(tk.END, "⚡ SWITCHED TO FAST SPEED (10 rounds/sec)\n")
                self.display_area.configure(state='disabled')
                self.display_area.see(tk.END)
            else:
                self.speed_button.config(text="Speed: Real-Time 🐌")
                # Update display
                self.display_area.configure(state='normal')
                self.display_area.insert(tk.END, "🐌 SWITCHED TO REAL-TIME SPEED (1 round/6sec)\n")
                self.display_area.configure(state='disabled')
                self.display_area.see(tk.END)
        else:
            print("[UI] No active casino feed to control speed")

    def start_tracking(self):
        """Start tracking using file data instead of browser."""
        print("[UI SIM] Starting file-based tracking...")
        
        # Initialize simulation scraper (reads from test data file)
        self.scraper = Scraper(self.data_queue)
        
        # Start scraper in thread
        self.scraper_thread = threading.Thread(target=self.scraper.start, daemon=True)
        self.scraper_thread.start()
        
        # Update button states
        self.track_button.config(state='disabled', text="Tracking (File Data)")
        self.stop_button.config(state='normal')
        self.is_tracking = True
        
        print("[UI SIM] File-based tracking started!")

    def stop_tracking(self):
        """Stop the file-based tracking."""
        if self.scraper:
            print("[UI SIM] Stopping file feed...")
            self.scraper.stop()
            if self.scraper_thread and self.scraper_thread.is_alive():
                self.scraper_thread.join(timeout=2)
            self.scraper = None

        self.track_button.config(state='normal', text="Start Tracking")
        self.stop_button.config(state='disabled')
        self.is_tracking = False

    def toggle_speed(self):
        """Toggle between fast and real-time speed"""
        if hasattr(self, 'casino_feed') and self.casino_feed:
            current_speed = self.casino_feed.toggle_speed()
            if current_speed == "fast":
                self.speed_button.config(text="Speed: Fast ⚡")
            else:
                self.speed_button.config(text="Speed: Real-time ⏰")
            print(f"[UI] Speed changed to: {current_speed}")

    def process_queues(self):
        try:
            # Status queue processing is removed.
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                payload = data.get('payloadData', data)
                if not payload: continue

                # Save data to the database
                self.db_manager.save_game_state(payload)

                game_id = payload.get('gameId')
                if not game_id: continue

                # Start session tracking if not already started
                if not self.current_session_id and self.shoe_manager.active_shoe_name in ["Shoe 1", "Shoe 2"]:
                    self.current_session_id = self.analytics_engine.start_session_tracking(self.shoe_manager.active_shoe_name)

                # --- Shoe and Card Counting Logic with Prediction Validation ---
                newly_dealt_cards = self.shoe_manager.process_game_state(payload)

                # Track individual cards for analytics and prediction validation
                self.current_dealing_position = 0
                self._track_dealt_cards_with_validation(payload, game_id)

                # If we are not tracking a specific shoe, we get all cards from the payload
                if self.shoe_manager.active_shoe_name not in ["Shoe 1", "Shoe 2"]:
                    all_cards_in_payload = []
                    if 'dealer' in payload and 'cards' in payload['dealer']:
                        all_cards_in_payload.extend([c['value'] for c in payload['dealer']['cards']])
                    if 'seats' in payload:
                        for seat in payload['seats'].values():
                            if 'first' in seat and 'cards' in seat['first']:
                                all_cards_in_payload.extend([c['value'] for c in seat['first']['cards']])

                    if self.card_counter.process_cards(all_cards_in_payload):
                        for card_rank in all_cards_in_payload:
                            if len(card_rank) > 0:
                                self.predictor.track_card(card_rank)
                        self.update_count_labels()
                elif newly_dealt_cards:
                    # If we are tracking, only count the newly dealt cards
                    card_strings = [str(c) for c in newly_dealt_cards]
                    if self.card_counter.process_cards(card_strings):
                        for card in newly_dealt_cards:
                            self.predictor.track_card(card.rank_str)
                        self.update_count_labels()
                else:
                    # Process all cards from payload when we have active shoe tracking
                    all_cards_in_payload = []
                    if 'dealer' in payload and 'cards' in payload['dealer']:
                        all_cards_in_payload.extend([c['value'] for c in payload['dealer']['cards']])
                    if 'seats' in payload:
                        for seat in payload['seats'].values():
                            if 'first' in seat and 'cards' in seat['first']:
                                all_cards_in_payload.extend([c['value'] for c in seat['first']['cards']])

                    if self.card_counter.process_cards(all_cards_in_payload):
                        for card_rank in all_cards_in_payload:
                            if len(card_rank) > 0:
                                self.predictor.track_card(card_rank)
                        self.update_count_labels()


                # --- Real-time Display Logic ---
                if game_id != self.last_game_id:
                    # End previous round prediction analysis
                    if self.last_game_id:
                        self.prediction_validator.end_round_analysis()
                    
                    self.round_counter += 1
                    self.last_game_id = game_id
                    self.current_dealing_position = 0
                    
                    # Start new round prediction tracking
                    active_shoe = self.shoe_manager.get_active_shoe()
                    if active_shoe and self.shoe_manager.active_shoe_name in ["Shoe 1", "Shoe 2"]:
                        self.prediction_validator.start_round_prediction(list(active_shoe.undealt_cards))
                    
                    # If it's a new shoe, reset everything
                    if "New Shoe" in str(payload):
                        self.card_counter.reset()
                        self.predictor.reset()
                        if self.current_session_id:
                            self.analytics_engine.end_session_tracking()
                        self.current_session_id = self.analytics_engine.start_session_tracking(self.shoe_manager.active_shoe_name)
                        self.update_game_display("--- NEW SHOE DETECTED, COUNTERS RESET ---\n")
                        self.update_count_labels()
                        self.round_counter = 1
                        self.round_line_map = {}

                    # Add a new line for the new round
                    formatted_state = self.format_game_state(payload, self.round_counter)
                    self.update_game_display(formatted_state + "\n")
                    # Mark the line number for future updates
                    current_line = self.display_area.index(tk.END).split('.')[0]
                    self.round_line_map[game_id] = f"{int(current_line) - 2}.0"
                else:
                    # Update the existing line for the current round
                    line_index = self.round_line_map.get(game_id)
                    if line_index:
                        formatted_state = self.format_game_state(payload, self.round_counter)
                        self.display_area.configure(state='normal')
                        self.display_area.delete(line_index, f"{line_index} lineend")
                        self.display_area.insert(line_index, formatted_state)
                        self.display_area.configure(state='disabled')

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queues)

    def format_game_state(self, payload, round_num):
        """Formats the raw JSON game data into a compact, single-line string."""
        parts = [f"Round {round_num}:"]

        # Dealer Info
        dealer = payload.get('dealer')
        if dealer:
            cards = ",".join([c.get('value', '?') for c in dealer.get('cards', [])])
            score = dealer.get('score', 'N/A')
            parts.append(f"D:[{cards}]({score})")

        # Player Info
        seats = payload.get('seats', {})
        for seat_num in sorted(seats.keys(), key=int):
            hand = seats.get(seat_num, {}).get('first')
            if hand and hand.get('cards'):
                cards = ",".join([c.get('value', '?') for c in hand.get('cards', [])])
                score = hand.get('score', 'N/A')
                state_char = hand.get('state', 'U')[0]
                parts.append(f"S{seat_num}:[{cards}]({score},{state_char})")

        return " | ".join(parts)

    def _track_dealt_cards_with_validation(self, payload, game_id):
        """Tracks each dealt card for analytics and prediction validation."""
        dealing_order = 1
        
        # Following the dealing sequence: Seat 6->5->4->3->2->1->0->Dealer face up
        # Then second cards: Seat 6->5->4->3->2->1->0->Dealer hole
        
        seats = payload.get('seats', {})
        dealer = payload.get('dealer', {})
        
        # Track first cards (initial dealing)
        for seat_num in [6, 5, 4, 3, 2, 1, 0]:
            if str(seat_num) in seats:
                seat_data = seats[str(seat_num)]
                if 'first' in seat_data and 'cards' in seat_data['first']:
                    cards = seat_data['first']['cards']
                    if len(cards) >= 1:
                        card_value = cards[0]['value']
                        self._track_single_card(game_id, card_value, dealing_order, seat_num, 'first_card')
                        dealing_order += 1
        
        # Track dealer's first card (face up)
        if dealer.get('cards') and len(dealer['cards']) >= 1:
            card_value = dealer['cards'][0]['value']
            self._track_single_card(game_id, card_value, dealing_order, -1, 'dealer_face_up')
            dealing_order += 1
        
        # Track second cards
        for seat_num in [6, 5, 4, 3, 2, 1, 0]:
            if str(seat_num) in seats:
                seat_data = seats[str(seat_num)]
                if 'first' in seat_data and 'cards' in seat_data['first']:
                    cards = seat_data['first']['cards']
                    if len(cards) >= 2:
                        card_value = cards[1]['value']
                        self._track_single_card(game_id, card_value, dealing_order, seat_num, 'second_card')
                        dealing_order += 1
        
        # Track dealer's hole card
        if dealer.get('cards') and len(dealer['cards']) >= 2:
            card_value = dealer['cards'][1]['value']
            self._track_single_card(game_id, card_value, dealing_order, -1, 'dealer_hole')
            dealing_order += 1
        
        # Track any additional cards (hits)
        for seat_num in [6, 5, 4, 3, 2, 1, 0]:
            if str(seat_num) in seats:
                seat_data = seats[str(seat_num)]
                if 'first' in seat_data and 'cards' in seat_data['first']:
                    cards = seat_data['first']['cards']
                    for i, card_data in enumerate(cards[2:], start=3):  # Start from 3rd card
                        card_value = card_data['value']
                        self._track_single_card(game_id, card_value, dealing_order, seat_num, f'hit_card_{i-2}')
                        dealing_order += 1
        
        # Track dealer's additional cards
        if dealer.get('cards') and len(dealer['cards']) > 2:
            for i, card_data in enumerate(dealer['cards'][2:], start=3):
                card_value = card_data['value']
                self._track_single_card(game_id, card_value, dealing_order, -1, f'dealer_hit_{i-2}')
                dealing_order += 1

    def _track_single_card(self, game_id, card_value, dealing_order, seat_number, card_type):
        """Tracks a single card for analytics and validation."""
        # Track for analytics
        if self.current_session_id:
            round_id = 1  # This would be derived from game_id in a more complete implementation
            self.analytics_engine.track_card_dealt(
                round_id, card_value, dealing_order, seat_number, card_type, dealing_order
            )
        
        # Add to prediction validation
        self.prediction_validator.add_dealt_card(card_value, dealing_order, seat_number)

    def update_count_labels(self):
        """Updates the running and true count labels in the UI."""
        running_count = self.card_counter.get_running_count()
        true_count = self.card_counter.get_true_count()
        cards_played = len(self.card_counter.seen_cards)
        decks_remaining = self.card_counter.get_decks_remaining()

        self.running_count_label.config(text=f"Running Count: {running_count}")
        self.true_count_label.config(text=f"True Count: {true_count:.2f}")
        self.cards_played_label.config(text=f"Cards Played: {cards_played}")
        self.decks_remaining_label.config(text=f"Decks Left: {decks_remaining:.1f}")
        self.sequence_prediction_label.config(text=self.predictor.get_prediction())
        
        # Update enhanced predictions
        self.update_predictions()
        self.update_zone_analysis()
        self.update_card_range_predictions()
        self.update_prediction_accuracy()

    def update_card_range_predictions(self):
        """Updates the next 5 card range predictions display."""
        active_shoe = self.shoe_manager.get_active_shoe()
        if not active_shoe or self.shoe_manager.active_shoe_name == "None":
            predictions = ["?"] * 5
        else:
            undealt_cards = list(active_shoe.undealt_cards)
            predictions = self.analytics_engine.get_real_time_predictions(undealt_cards, [])
        
        # Color coding for different ranges
        color_map = {
            "Low": "#FF6B6B",   # Red for low cards (bad for player)
            "Mid": "#FFE66D",   # Yellow for mid cards (neutral)
            "High": "#4ECDC4",  # Green for high cards (good for player)
            "Unknown": "#95A5A6" # Gray for unknown
        }
        
        for i, (label, prediction) in enumerate(zip(self.card_range_labels, predictions)):
            label.config(text=prediction, foreground=color_map.get(prediction, "#000000"))

    def update_prediction_accuracy(self):
        """Updates the prediction accuracy display."""
        accuracy_stats = self.prediction_validator.get_prediction_accuracy_stats()
        accuracy = accuracy_stats.get('accuracy', 0.0)
        total = accuracy_stats.get('total_predictions', 0)
        
        if total > 0:
            self.prediction_accuracy_label.config(
                text=f"Prediction Accuracy: {accuracy:.1%} ({total} predictions)",
                foreground="green" if accuracy > 0.6 else "orange" if accuracy > 0.4 else "red"
            )
        else:
            self.prediction_accuracy_label.config(text="Prediction Accuracy: Calculating...", foreground="gray")

    def update_zone_analysis(self):
        """Updates the zone analysis label."""
        active_shoe_name = self.shoe_manager.active_shoe_name
        if active_shoe_name != "None":
            shuffle_manager = self.shoe_manager.shuffle_managers.get(active_shoe_name)
            if shuffle_manager:
                summaries = shuffle_manager.get_all_zone_summaries()
                self.zone_analysis_label.config(text="\n".join(summaries))
            else:
                self.zone_analysis_label.config(text="No shuffle manager for this shoe.")
        else:
            self.zone_analysis_label.config(text="Zone analysis requires a tracked shoe.")


    def update_predictions(self):
        """Updates the prediction label based on the active shoe."""
        active_shoe = self.shoe_manager.get_active_shoe()
        prediction_text = "Next 10-Val Window: [ ? | ? | ? | <10> | ? | ? | ? ]"

        if active_shoe and self.shoe_manager.active_shoe_name != "None":
            undealt_cards = list(active_shoe.undealt_cards)

            # Find the index of the next 10-value card
            next_ten_index = -1
            for i, card in enumerate(undealt_cards):
                if card.value == 10:
                    next_ten_index = i
                    break

            if next_ten_index != -1:
                # Get the 7-card window: 3 before, the 10, 3 after
                start = max(0, next_ten_index - 3)
                end = min(len(undealt_cards), next_ten_index + 4)
                window = undealt_cards[start:end]

                card_strs = []
                for card in window:
                    if card.value == 10:
                        card_strs.append(f"<{str(card)}>")
                    else:
                        card_strs.append(str(card))

                prediction_text = f"Next 10-Val Window: [ {' | '.join(card_strs)} ]"

        self.prediction_label.config(text=prediction_text)


    def update_game_display(self, message):
        """This method is now only for writing game data to the display."""
        self.display_area.configure(state='normal')
        self.display_area.insert(tk.END, f"{message}")
        self.display_area.configure(state='disabled')
        self.display_area.see(tk.END)

    def on_shoe_select(self, selected_shoe):
        """Callback for when a new shoe is selected from the dropdown."""
        # End current session if one is active
        if self.current_session_id:
            final_stats = {
                'total_rounds': self.round_counter,
                'total_cards_dealt': len(self.card_counter.seen_cards),
                'win_rate': 0.5,  # Placeholder - would calculate from actual results
                'dealer_wins': 0,  # Would track these from game results
                'player_wins': 0,
                'pushes': 0
            }
            self.analytics_engine.end_session_tracking(final_stats)
            self.current_session_id = None

        self.shoe_manager.set_active_shoe(selected_shoe)
        print(f"[UI] Active shoe changed to: {selected_shoe}")
        
        # Start new session tracking if not "None"
        if selected_shoe != "None":
            self.current_session_id = self.analytics_engine.start_session_tracking(selected_shoe)
        
        # Reset UI and counters when changing shoes
        self.display_area.configure(state='normal')
        self.display_area.delete('1.0', tk.END)
        self.display_area.configure(state='disabled')
        self.card_counter.reset()
        self.update_count_labels()
        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None

    def create_analytics_tab(self, parent):
        """Create the enhanced Analytics & Predictions tab."""
        # Main container with scrollable frame
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎰 Enhanced Analytics & Predictions", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Create notebook for different analytics sections
        analytics_notebook = ttk.Notebook(main_frame)
        analytics_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 1. Performance Analysis Tab
        perf_frame = ttk.Frame(analytics_notebook)
        analytics_notebook.add(perf_frame, text="📊 Performance Analysis")
        self.create_performance_section(perf_frame)
        
        # 2. Recommendations Tab
        rec_frame = ttk.Frame(analytics_notebook)
        analytics_notebook.add(rec_frame, text="🎯 Recommendations")
        self.create_recommendations_section(rec_frame)
        
        # 3. Predictions Tab
        pred_frame = ttk.Frame(analytics_notebook)
        analytics_notebook.add(pred_frame, text="🔮 Predictions")
        self.create_predictions_section(pred_frame)
        
        # 4. Live Status Tab
        status_frame = ttk.Frame(analytics_notebook)
        analytics_notebook.add(status_frame, text="📡 Live Status")
        self.create_live_status_section(status_frame)
        
        # Refresh button
        refresh_btn = ttk.Button(main_frame, text="🔄 Refresh Analytics", 
                               command=self.refresh_all_analytics)
        refresh_btn.pack(pady=10)
        
        # Load initial data
        self.root.after(1000, self.refresh_all_analytics)
    
    def create_performance_section(self, parent):
        """Create the performance analysis section."""
        # Shoe Performance
        shoe_frame = ttk.LabelFrame(parent, text="🎰 Shoe Performance Analysis")
        shoe_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.shoe_performance_display = tk.Text(shoe_frame, height=8, wrap=tk.WORD, 
                                              font=("Consolas", 10))
        shoe_scroll = ttk.Scrollbar(shoe_frame, orient="vertical", command=self.shoe_performance_display.yview)
        self.shoe_performance_display.configure(yscrollcommand=shoe_scroll.set)
        self.shoe_performance_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        shoe_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Seat Performance
        seat_frame = ttk.LabelFrame(parent, text="🪑 Seat Performance Analysis")
        seat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.seat_performance_display = tk.Text(seat_frame, height=8, wrap=tk.WORD, 
                                              font=("Consolas", 10))
        seat_scroll = ttk.Scrollbar(seat_frame, orient="vertical", command=self.seat_performance_display.yview)
        self.seat_performance_display.configure(yscrollcommand=seat_scroll.set)
        self.seat_performance_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        seat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_recommendations_section(self, parent):
        """Create the recommendations section."""
        # Decision Recommendations
        rec_frame = ttk.LabelFrame(parent, text="🎯 Decision Recommendations")
        rec_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.recommendations_display = tk.Text(rec_frame, height=10, wrap=tk.WORD, 
                                             font=("Arial", 11))
        rec_scroll = ttk.Scrollbar(rec_frame, orient="vertical", command=self.recommendations_display.yview)
        self.recommendations_display.configure(yscrollcommand=rec_scroll.set)
        self.recommendations_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rec_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary Stats
        summary_frame = ttk.LabelFrame(parent, text="📈 Session Summary")
        summary_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.session_summary_display = tk.Text(summary_frame, height=6, wrap=tk.WORD, 
                                             font=("Arial", 10))
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=self.session_summary_display.yview)
        self.session_summary_display.configure(yscrollcommand=summary_scroll.set)
        self.session_summary_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_predictions_section(self, parent):
        """Create the predictions section."""
        # Prediction Accuracy
        acc_frame = ttk.LabelFrame(parent, text="🎯 Prediction Accuracy")
        acc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.accuracy_display = tk.Text(acc_frame, height=8, wrap=tk.WORD, 
                                      font=("Arial", 11))
        acc_scroll = ttk.Scrollbar(acc_frame, orient="vertical", command=self.accuracy_display.yview)
        self.accuracy_display.configure(yscrollcommand=acc_scroll.set)
        self.accuracy_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        acc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Card Range Predictions
        pred_frame = ttk.LabelFrame(parent, text="🃏 Card Range Predictions")
        pred_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.prediction_display = tk.Text(pred_frame, height=8, wrap=tk.WORD, 
                                        font=("Consolas", 10))
        pred_scroll = ttk.Scrollbar(pred_frame, orient="vertical", command=self.prediction_display.yview)
        self.prediction_display.configure(yscrollcommand=pred_scroll.set)
        self.prediction_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pred_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_live_status_section(self, parent):
        """Create the live status section."""
        # Current Status
        status_frame = ttk.LabelFrame(parent, text="📡 Live Tracking Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.live_status_display = tk.Text(status_frame, height=12, wrap=tk.WORD, 
                                         font=("Arial", 10))
        status_scroll = ttk.Scrollbar(status_frame, orient="vertical", command=self.live_status_display.yview)
        self.live_status_display.configure(yscrollcommand=status_scroll.set)
        self.live_status_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def refresh_all_analytics(self):
        """Refresh all analytics displays with latest data."""
        try:
            self.refresh_performance_analysis()
            self.refresh_recommendations()
            self.refresh_predictions()
            self.refresh_live_status()
        except Exception as e:
            print(f"Error refreshing analytics: {e}")
    
    def refresh_performance_analysis(self):
        """Refresh performance analysis displays."""
        try:
            # Get shoe performance
            analysis = self.analytics_engine.get_shoe_performance_analysis(hours_back=24)
            
            # Update shoe performance display
            if hasattr(self, 'shoe_performance_display'):
                self.shoe_performance_display.configure(state='normal')
                self.shoe_performance_display.delete('1.0', tk.END)
                
                shoe_text = "🎰 SHOE PERFORMANCE ANALYSIS\n"
                shoe_text += "=" * 50 + "\n\n"
                
                shoe_performance = analysis.get('shoe_performance', [])
                if shoe_performance:
                    for i, shoe in enumerate(shoe_performance[:5]):  # Top 5
                        rank = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                        win_rate = shoe.get('win_rate', 0)
                        sessions = shoe.get('sessions', 0)
                        
                        status = "🔥 HOT" if win_rate > 0.55 else "❄️ COLD" if win_rate < 0.45 else "⚡ WARM"
                        
                        shoe_text += f"{rank} {shoe.get('name', 'Unknown')}\n"
                        shoe_text += f"   Win Rate: {win_rate:.1%} {status}\n"
                        shoe_text += f"   Sessions: {sessions}\n"
                        shoe_text += f"   Profit Level: {'HIGH' if win_rate > 0.55 else 'LOW' if win_rate < 0.45 else 'MEDIUM'}\n\n"
                else:
                    shoe_text += "No shoe data available yet.\nStart tracking to see performance analysis!"
                
                self.shoe_performance_display.insert('1.0', shoe_text)
                self.shoe_performance_display.configure(state='disabled')
            
            # Update seat performance display
            if hasattr(self, 'seat_performance_display'):
                self.seat_performance_display.configure(state='normal')
                self.seat_performance_display.delete('1.0', tk.END)
                
                seat_text = "🪑 SEAT PERFORMANCE ANALYSIS\n"
                seat_text += "=" * 50 + "\n\n"
                
                seat_performance = analysis.get('seat_performance', [])
                if seat_performance:
                    for seat in seat_performance:
                        seat_num = seat.get('seat_number', 0)
                        win_rate = seat.get('win_rate', 0)
                        rounds = seat.get('total_rounds', 0)
                        
                        performance = "🌟 EXCELLENT" if win_rate > 0.55 else "❌ POOR" if win_rate < 0.45 else "✅ GOOD"
                        
                        seat_text += f"Seat {seat_num}: {win_rate:.1%} {performance}\n"
                        seat_text += f"   Rounds played: {rounds}\n"
                        seat_text += f"   Recommendation: {'SIT HERE' if win_rate > 0.52 else 'AVOID' if win_rate < 0.45 else 'NEUTRAL'}\n\n"
                else:
                    seat_text += "No seat data available yet.\nStart tracking to see seat analysis!"
                
                self.seat_performance_display.insert('1.0', seat_text)
                self.seat_performance_display.configure(state='disabled')
                
        except Exception as e:
            print(f"Error refreshing performance analysis: {e}")
    
    def refresh_recommendations(self):
        """Refresh recommendations display."""
        try:
            recommendations = self.analytics_engine.get_decision_recommendations()
            
            if hasattr(self, 'recommendations_display'):
                self.recommendations_display.configure(state='normal')
                self.recommendations_display.delete('1.0', tk.END)
                
                rec_text = "🎯 DECISION RECOMMENDATIONS\n"
                rec_text += "=" * 50 + "\n\n"
                
                should_play = recommendations.get('should_play', False)
                confidence = recommendations.get('confidence_level', 'unknown')
                
                # Main recommendation
                if should_play:
                    rec_text += "🟢 RECOMMENDATION: PLAY NOW!\n\n"
                    rec_text += "✅ Conditions are favorable for profitable play.\n\n"
                else:
                    rec_text += "🔴 RECOMMENDATION: WAIT\n\n"
                    rec_text += "⚠️ Current conditions are not optimal.\n\n"
                
                # Details
                rec_text += f"🎯 Confidence Level: {confidence.upper()}\n"
                rec_text += f"🎰 Best Shoe: {recommendations.get('best_shoe', 'Unknown')}\n"
                rec_text += f"🪑 Best Seat: {recommendations.get('best_seat', 'Any')}\n\n"
                
                # Reasoning
                reasoning = recommendations.get('reasoning', [])
                if reasoning:
                    rec_text += "💡 REASONING:\n"
                    for reason in reasoning[:3]:  # Top 3 reasons
                        rec_text += f"   • {reason}\n"
                else:
                    rec_text += "💡 Analysis based on historical performance patterns.\n"
                
                self.recommendations_display.insert('1.0', rec_text)
                self.recommendations_display.configure(state='disabled')
            
            # Update session summary
            if hasattr(self, 'session_summary_display'):
                self.session_summary_display.configure(state='normal')
                self.session_summary_display.delete('1.0', tk.END)
                
                summary_text = "📈 SESSION SUMMARY\n"
                summary_text += "=" * 30 + "\n\n"
                summary_text += f"🎲 Rounds Tracked: {self.round_counter}\n"
                summary_text += f"🃏 Cards Seen: {len(self.card_counter.seen_cards)}\n"
                summary_text += f"👁️ Current Count: {self.card_counter.running_count}\n"
                summary_text += f"🎰 Active Shoe: {self.shoe_manager.active_shoe_name}\n"
                summary_text += f"📊 Analytics Session: {'Active' if self.current_session_id else 'None'}\n"
                
                self.session_summary_display.insert('1.0', summary_text)
                self.session_summary_display.configure(state='disabled')
                
        except Exception as e:
            print(f"Error refreshing recommendations: {e}")
    
    def refresh_predictions(self):
        """Refresh predictions display."""
        try:
            if hasattr(self, 'accuracy_display'):
                accuracy_stats = self.prediction_validator.get_prediction_accuracy_stats()
                
                self.accuracy_display.configure(state='normal')
                self.accuracy_display.delete('1.0', tk.END)
                
                acc_text = "🎯 PREDICTION ACCURACY\n"
                acc_text += "=" * 40 + "\n\n"
                
                accuracy = accuracy_stats.get('accuracy', 0)
                total_preds = accuracy_stats.get('total_predictions', 0)
                
                acc_text += f"🎯 Overall Accuracy: {accuracy:.1%}\n"
                acc_text += f"📊 Total Predictions: {total_preds}\n"
                acc_text += f"📈 Performance: {'EXCELLENT' if accuracy > 0.7 else 'GOOD' if accuracy > 0.6 else 'IMPROVING'}\n\n"
                
                trends = accuracy_stats.get('trends', 'stable')
                acc_text += f"📉 Trend: {trends.upper()}\n"
                
                if accuracy > 0:
                    acc_text += f"\n💡 The prediction system is learning and improving!\n"
                    acc_text += f"   Accuracy above 60% indicates reliable predictions.\n"
                else:
                    acc_text += f"\n🔄 Collecting data to establish prediction accuracy...\n"
                
                self.accuracy_display.insert('1.0', acc_text)
                self.accuracy_display.configure(state='disabled')
            
            # Update card range predictions
            if hasattr(self, 'prediction_display'):
                self.prediction_display.configure(state='normal')
                self.prediction_display.delete('1.0', tk.END)
                
                pred_text = "🃏 CARD RANGE PREDICTIONS\n"
                pred_text += "=" * 40 + "\n\n"
                
                # Get current count for predictions
                current_count = self.card_counter.running_count
                
                if current_count > 0:
                    pred_text += "🔥 HIGH CARDS LIKELY\n"
                    pred_text += f"   Count: +{current_count}\n"
                    pred_text += "   Expect: 10s, Jacks, Queens, Kings, Aces\n"
                    pred_text += "   Strategy: Increase bets, favorable for player\n\n"
                elif current_count < 0:
                    pred_text += "❄️ LOW CARDS LIKELY\n"
                    pred_text += f"   Count: {current_count}\n"
                    pred_text += "   Expect: 2s, 3s, 4s, 5s, 6s\n"
                    pred_text += "   Strategy: Minimum bets, favor dealer\n\n"
                else:
                    pred_text += "⚖️ NEUTRAL DECK\n"
                    pred_text += "   Count: 0\n"
                    pred_text += "   Expect: Balanced card distribution\n"
                    pred_text += "   Strategy: Standard basic strategy\n\n"
                
                pred_text += f"🎲 Cards remaining: ~{len(self.card_counter.seen_cards)} seen\n"
                pred_text += f"📊 Deck penetration: In progress...\n"
                
                self.prediction_display.insert('1.0', pred_text)
                self.prediction_display.configure(state='disabled')
                
        except Exception as e:
            print(f"Error refreshing predictions: {e}")
    
    def refresh_live_status(self):
        """Refresh live status display."""
        try:
            if hasattr(self, 'live_status_display'):
                self.live_status_display.configure(state='normal')
                self.live_status_display.delete('1.0', tk.END)
                
                status_text = "📡 LIVE TRACKING STATUS\n"
                status_text += "=" * 50 + "\n\n"
                
                # Connection status
                if self.is_tracking:
                    status_text += "🟢 STATUS: ACTIVELY TRACKING\n"
                    status_text += f"🌐 Connected to: {self.url_var.get()}\n"
                else:
                    status_text += "🔴 STATUS: NOT TRACKING\n"
                    status_text += "⚠️ Click 'Start Tracking' to begin\n"
                
                status_text += f"\n📊 CURRENT SESSION:\n"
                status_text += f"   🎰 Shoe: {self.shoe_manager.active_shoe_name}\n"
                status_text += f"   🎲 Round: {self.round_counter}\n"
                status_text += f"   👁️ Running Count: {self.card_counter.running_count}\n"
                status_text += f"   🃏 Cards Tracked: {len(self.card_counter.seen_cards)}\n"
                
                # Demo status
                import os
                if os.path.exists('demo_environment_summary.json'):
                    status_text += f"\n🎮 DEMO MODE ACTIVE\n"
                    status_text += f"   📈 Historical data loaded\n"
                    status_text += f"   🎯 Analytics features enabled\n"
                
                if os.path.exists('live_demo_feed.json'):
                    status_text += f"   🔄 Live demo running\n"
                
                status_text += f"\n💡 NEXT STEPS:\n"
                if not self.is_tracking:
                    status_text += f"   1. Enter game URL\n"
                    status_text += f"   2. Click 'Start Tracking'\n"
                    status_text += f"   3. Monitor Analytics tab\n"
                else:
                    status_text += f"   1. Monitor game for new rounds\n"
                    status_text += f"   2. Check recommendations regularly\n"
                    status_text += f"   3. Use insights for optimal play\n"
                
                self.live_status_display.insert('1.0', status_text)
                self.live_status_display.configure(state='disabled')
                
        except Exception as e:
            print(f"Error refreshing live status: {e}")


    def mark_end_of_shoe(self):
        """Callback for the 'Mark End of Shoe' button."""
        print("[UI] 'Mark End of Shoe' button pressed.")
        current_shoe = self.shoe_manager.active_shoe_name
        
        # End current analytics session
        if self.current_session_id:
            final_stats = {
                'total_rounds': self.round_counter,
                'total_cards_dealt': len(self.card_counter.seen_cards),
                'win_rate': 0.5,  # Placeholder - would calculate from actual results
                'dealer_wins': 0,  # Would track these from game results
                'player_wins': 0,
                'pushes': 0
            }
            self.analytics_engine.end_session_tracking(final_stats)
            self.current_session_id = None
        
        if self.shoe_manager.end_current_shoe():
            self.update_game_display(f"--- End of {current_shoe} Marked ---\nRemaining cards are ready for shuffling.\n")

            # Automatically switch to the other shoe
            next_shoe = "Shoe 2" if current_shoe == "Shoe 1" else "Shoe 1"
            self.shoe_var.set(next_shoe) # This will trigger on_shoe_select
            self.on_shoe_select(next_shoe)
            self.update_game_display(f"--- Switched to {next_shoe} ---\n")
            
            # Refresh analytics display
            self.refresh_analytics()
        else:
            self.update_game_display("--- No active shoe to end ---\n")

    def perform_shuffle(self):
        """Callback for the 'Perform Shuffle' button."""
        print("[UI] 'Perform Shuffle' button pressed.")
        # This is a placeholder for the complex shuffle logic.
        # In a real implementation, we would build a list of operations
        # from the form and pass them to the shoe_manager.

        # For now, we will just call the placeholder shuffle in the shoe manager.
        # We also need to select which shoe to apply the shuffle to.
        # Let's assume we shuffle and apply it to "Shoe 1".

        shuffle_params = {
            "regions": self.regions_var.get(),
            "riffles": self.riffles_var.get()
        }
        self.shoe_manager.perform_shuffle("Shoe 1", shuffle_params)
        self.update_game_display("--- Shuffle Performed on Shoe 1 ---\n")

    def refresh_analytics(self):
        """Refreshes the analytics display with current data."""
        try:
            # Get comprehensive analysis
            analysis = self.analytics_engine.get_shoe_performance_analysis(hours_back=24)
            recommendations = self.analytics_engine.get_decision_recommendations()
            
            # Update performance summary
            self.perf_summary_text.delete('1.0', tk.END)
            summary_text = self._format_performance_summary(analysis)
            self.perf_summary_text.insert('1.0', summary_text)
            
            # Update recommendations
            self.recommendation_text.delete('1.0', tk.END)
            rec_text = self._format_recommendations(recommendations)
            self.recommendation_text.insert('1.0', rec_text)
            
            print("[Analytics] Display refreshed successfully")
            
        except Exception as e:
            print(f"[Analytics] Error refreshing display: {e}")

    def _format_performance_summary(self, analysis):
        """Formats the performance analysis for display."""
        summary = "=== PERFORMANCE SUMMARY (Last 24 Hours) ===\n\n"
        
        # Shoe Performance
        summary += "SHOE PERFORMANCE:\n"
        shoes = analysis.get('shoe_performance', [])
        if shoes:
            for shoe in shoes:
                summary += f"  • {shoe['name']}: {shoe['win_rate']:.1%} win rate "
                summary += f"({shoe['sessions']} sessions, {shoe['avg_rounds']:.0f} avg rounds)\n"
                summary += f"    Player Wins: {shoe['player_wins']}, Dealer Wins: {shoe['dealer_wins']}\n"
        else:
            summary += "  No completed shoe sessions found\n"
        
        summary += "\nSEAT PERFORMANCE:\n"
        seats = analysis.get('seat_performance', [])
        if seats:
            for seat in seats:
                summary += f"  • Seat {seat['seat_number']}: {seat['win_rate']:.1%} win rate "
                summary += f"({seat['total_rounds']} rounds, {seat['sessions']} sessions)\n"
        else:
            summary += "  No seat performance data available\n"
        
        # Prediction Accuracy
        pred_acc = analysis.get('prediction_accuracy', {})
        summary += f"\nPREDICTION ACCURACY: {pred_acc.get('accuracy', 0):.1%} "
        summary += f"({pred_acc.get('total_predictions', 0)} predictions)\n"
        
        return summary

    def _format_recommendations(self, recommendations):
        """Formats the recommendations for display."""
        rec_text = "=== DECISION RECOMMENDATIONS ===\n\n"
        
        should_play = recommendations.get('should_play', False)
        confidence = recommendations.get('confidence_level', 'Low')
        
        if should_play:
            rec_text += "🟢 RECOMMENDATION: FAVORABLE CONDITIONS FOR PLAY\n"
        else:
            rec_text += "🔴 RECOMMENDATION: WAIT FOR BETTER CONDITIONS\n"
        
        rec_text += f"Confidence Level: {confidence}\n\n"
        
        best_shoe = recommendations.get('best_shoe')
        if best_shoe:
            rec_text += f"Best Shoe: {best_shoe}\n"
        
        best_seat = recommendations.get('best_seat')
        if best_seat is not None:
            rec_text += f"Best Seat: {best_seat}\n"
        
        rec_text += "\nREASONS:\n"
        for reason in recommendations.get('reasons', []):
            rec_text += f"  • {reason}\n"
        
        return rec_text

    def export_analysis_report(self):
        """Exports a comprehensive analysis report."""
        try:
            filename = self.analytics_engine.export_analysis_report()
            self.update_game_display(f"--- Analysis report exported to {filename} ---\n")
            print(f"[Analytics] Report exported to {filename}")
        except Exception as e:
            print(f"[Analytics] Error exporting report: {e}")

    def reset_current_session(self):
        """Resets the current tracking session."""
        if self.current_session_id:
            self.analytics_engine.end_session_tracking()
            self.current_session_id = None
        
        # Start new session if actively tracking
        if self.shoe_manager.active_shoe_name != "None":
            self.current_session_id = self.analytics_engine.start_session_tracking(self.shoe_manager.active_shoe_name)
        
        self.update_game_display("--- Session Reset ---\n")
        print("[Analytics] Session reset")

    def start_live_demo_monitor(self):
        """Start monitoring for live demo data."""
        self.check_live_demo_data()
        self.load_simulation_data()  # Load existing simulation data
        
    def load_simulation_data(self):
        """Load recent simulation data into Live Tracker display."""
        try:
            # Get recent games from database
            import sqlite3
            conn = sqlite3.connect('blackjack_data.db')
            cursor = conn.cursor()
            
            # Get the most recent 20 games
            cursor.execute("""
                SELECT round_number, shoe_id, dealer_cards, player_cards, outcome, payout, timestamp
                FROM games 
                ORDER BY timestamp DESC 
                LIMIT 20
            """)
            
            recent_games = cursor.fetchall()
            conn.close()
            
            if recent_games:
                # Update the live display area with simulation data
                self.display_area.configure(state='normal')
                self.display_area.delete('1.0', tk.END)
                
                header = "🎰 SIMULATION DATA - Recent Games\n"
                header += "=" * 60 + "\n\n"
                self.display_area.insert(tk.END, header)
                
                for game in reversed(recent_games):  # Show chronologically
                    round_num, shoe, dealer, player, outcome, payout, timestamp = game
                    
                    # Format the game display
                    game_text = f"Round {round_num} [{shoe}]\n"
                    game_text += f"  Dealer: {dealer}  |  Player: {player}\n"
                    game_text += f"  Result: {outcome}  |  Payout: ${payout}\n"
                    game_text += f"  Time: {timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp}\n"
                    game_text += "-" * 50 + "\n"
                    
                    # Color code by outcome
                    if outcome == "Win":
                        self.display_area.insert(tk.END, game_text, "win_tag")
                    else:
                        self.display_area.insert(tk.END, game_text, "loss_tag")
                
                # Configure text tags for coloring
                self.display_area.tag_configure("win_tag", foreground="green")
                self.display_area.tag_configure("loss_tag", foreground="red")
                
                self.display_area.configure(state='disabled')
                self.display_area.see(tk.END)  # Scroll to bottom
                
                # Update the display label
                self.display_label.configure(text=f"Simulation Data - {len(recent_games)} Recent Games")
                
                # Update tracking indicators
                self.is_tracking = True
                self.current_shoe = recent_games[0][1] if recent_games else "Premium Shoe 1"
                
                print(f"[Live Demo] Loaded {len(recent_games)} recent games from simulation")
            
        except Exception as e:
            print(f"[Live Demo] Error loading simulation data: {e}")
        
    def check_live_demo_data(self):
        """Check for live demo data and update display."""
        try:
            import os
            import json
            
            # Check for live demo feed
            if os.path.exists('live_demo_feed.json'):
                with open('live_demo_feed.json', 'r') as f:
                    demo_data = json.load(f)
                
                # Update analytics display with live data
                if demo_data.get('status') == 'active':
                    self.live_demo_active = True
                    
                    # Get latest cards
                    recent_cards = demo_data.get('cards_dealt', [])[-5:]  # Last 5 cards
                    if recent_cards:
                        demo_info = "🎮 LIVE DEMO ACTIVE\n"
                        demo_info += f"Round: {demo_data.get('current_round', 0)}\n"
                        demo_info += "Recent cards:\n"
                        
                        for card_info in recent_cards:
                            position = "Dealer" if card_info.get('is_dealer') else f"Seat {card_info.get('seat')}"
                            demo_info += f"  {card_info.get('card')} → {position}\n"
                        
                        # Update prediction display if available
                        if hasattr(self, 'prediction_display'):
                            self.prediction_display.configure(text=demo_info)
                    
                    # Refresh analytics
                    self.refresh_analytics_display()
            
            # Check for demo environment status
            if os.path.exists('demo_environment_summary.json'):
                with open('demo_environment_summary.json', 'r') as f:
                    env_data = json.load(f)
                
                if env_data.get('environment_ready'):
                    # Show environment status in analytics
                    if hasattr(self, 'analytics_summary_display'):
                        summary_text = "📊 DEMO ENVIRONMENT READY\n\n"
                        summary_text += f"Historical Data: {env_data['historical_data']['total_rounds']} rounds\n"
                        summary_text += f"Best Shoe: {env_data['key_insights']['best_shoe']}\n"
                        summary_text += f"Best Seats: {env_data['key_insights']['best_seats']}\n"
                        summary_text += f"Should Play: {'YES' if env_data['key_insights']['should_play_now'] else 'NO'}\n"
                        summary_text += f"Confidence: {env_data['key_insights']['confidence_level']}\n"
                        
                        self.analytics_summary_display.configure(text=summary_text)
            
            # Reload simulation data periodically
            if not hasattr(self, '_last_sim_check'):
                self._last_sim_check = 0
            
            import time
            if time.time() - self._last_sim_check > 10:  # Every 10 seconds
                self.load_simulation_data()
                self._last_sim_check = time.time()
        
        except Exception as e:
            pass  # Silently ignore demo data errors
        
        # Schedule next check
        self.root.after(2000, self.check_live_demo_data)  # Check every 2 seconds

    def refresh_analytics_display(self):
        """Refresh the analytics display with latest data."""
        try:
            if hasattr(self, 'analytics_engine') and self.analytics_engine:
                # Get fresh analytics
                analysis = self.analytics_engine.get_shoe_performance_analysis(hours_back=3)
                recommendations = self.analytics_engine.get_decision_recommendations()
                
                # Update displays if they exist
                if hasattr(self, 'recommendations_display'):
                    rec_text = f"🎯 RECOMMENDATIONS\n\n"
                    rec_text += f"Should Play: {'YES ✅' if recommendations.get('should_play') else 'NO ❌'}\n"
                    rec_text += f"Best Shoe: {recommendations.get('best_shoe', 'N/A')}\n"
                    rec_text += f"Best Seat: {recommendations.get('best_seat', 'N/A')}\n"
                    rec_text += f"Confidence: {recommendations.get('confidence_level', 'unknown')}\n"
                    
                    self.recommendations_display.configure(text=rec_text)
                
                # Update prediction accuracy if available
                if hasattr(self, 'prediction_validator') and hasattr(self, 'accuracy_display'):
                    accuracy_stats = self.prediction_validator.get_prediction_accuracy_stats()
                    acc_text = f"🎯 PREDICTION ACCURACY\n\n"
                    acc_text += f"Accuracy: {accuracy_stats.get('accuracy', 0):.1%}\n"
                    acc_text += f"Total Predictions: {accuracy_stats.get('total_predictions', 0)}\n"
                    acc_text += f"Trend: {accuracy_stats.get('trends', 'stable')}\n"
                    
                    self.accuracy_display.configure(text=acc_text)
        
        except Exception as e:
            pass  # Silently handle refresh errors

    def on_closing(self):
        self.stop_tracking()
        
        # End current analytics session
        if self.current_session_id:
            final_stats = {
                'total_rounds': self.round_counter,
                'total_cards_dealt': len(self.card_counter.seen_cards),
                'win_rate': 0.5,  # Placeholder
                'dealer_wins': 0,
                'player_wins': 0,
                'pushes': 0
            }
            self.analytics_engine.end_session_tracking(final_stats)
        
        if self.db_manager:
            self.db_manager.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
