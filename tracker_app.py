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
        self.shoe_manager = ShoeManager()
        self.predictor = SequencePredictor()

        # UI State
        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None

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

        self.notebook.add(self.live_tracker_tab, text="Live Tracker")
        self.notebook.add(self.shoe_tracking_tab, text="Shoe Tracking")

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

        self.shoe_var = tk.StringVar(value="None")
        self.shoe_select_menu = ttk.OptionMenu(self.shoe_controls_frame, self.shoe_var, "None", "Shoe 1", "Shoe 2", command=self.on_shoe_select)
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
        self.sequence_prediction_label.pack()

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

    def start_tracking(self):
        print("[UI] Starting scraper...")
        self.scraper = Scraper(self.data_queue) # No longer needs status_queue
        self.scraper_thread = threading.Thread(target=self.scraper.start, daemon=True)
        self.scraper_thread.start()

        self.track_button.config(state='disabled')
        self.stop_button.config(state='normal')

    def stop_tracking(self):
        if self.scraper:
            print("[UI] Sending stop signal to scraper...")
            self.scraper.stop()
            self.scraper_thread.join(timeout=2) # Wait a bit for the thread to finish
            self.scraper = None

        self.track_button.config(state='normal')
        self.stop_button.config(state='disabled')

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

                # --- Shoe and Card Counting Logic is now centralized ---
                # The shoe manager processes the state, deals cards from the tracked shoe,
                # and returns only the newly seen cards for counting.
                newly_dealt_cards = self.shoe_manager.process_game_state(payload)

                # If we are not tracking a specific shoe, we get all cards from the payload
                # and pass them to the card counter directly.
                if self.shoe_manager.active_shoe_name == "None":
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


                # --- Real-time Display Logic ---
                if game_id != self.last_game_id:
                    self.round_counter += 1
                    self.last_game_id = game_id
                    # If it's a new shoe, reset everything
                    if "New Shoe" in str(payload):
                        self.card_counter.reset()
                        self.predictor.reset()
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
        self.update_predictions()
        self.update_zone_analysis()

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
        self.shoe_manager.set_active_shoe(selected_shoe)
        print(f"[UI] Active shoe changed to: {selected_shoe}")
        # We also need to reset the UI and counters when changing shoes
        self.display_area.configure(state='normal')
        self.display_area.delete('1.0', tk.END)
        self.display_area.configure(state='disabled')
        self.card_counter.reset()
        self.update_count_labels()
        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None


    def mark_end_of_shoe(self):
        """Callback for the 'Mark End of Shoe' button."""
        print("[UI] 'Mark End of Shoe' button pressed.")
        current_shoe = self.shoe_manager.active_shoe_name
        if self.shoe_manager.end_current_shoe():
            self.update_game_display(f"--- End of {current_shoe} Marked ---\nRemaining cards are ready for shuffling.\n")

            # Automatically switch to the other shoe
            next_shoe = "Shoe 2" if current_shoe == "Shoe 1" else "Shoe 1"
            self.shoe_var.set(next_shoe) # This will trigger on_shoe_select
            self.on_shoe_select(next_shoe)
            self.update_game_display(f"--- Switched to {next_shoe} ---\n")
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


    def on_closing(self):
        self.stop_tracking()
        if self.db_manager:
            self.db_manager.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
