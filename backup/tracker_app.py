import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import os
import threading
import queue
import json
from scraper import Scraper
from card_counter import CardCounter
from strategy import get_strategy_action, get_bet_recommendation
from shoe_manager import ShoeManager

class BlackjackTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack Tracker & Predictor")
        self.root.geometry("1200x800")

        self.scraper = None
        self.scraper_thread = None
        self.data_queue = queue.Queue()
        self.card_counter = CardCounter()
        self.shoe_manager = ShoeManager()

        # UI State
        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None

        # UI Variables
        self.url_var = tk.StringVar(value="https://casino.draftkings.com")
        self.running_count_var = tk.StringVar(value="Running Count: 0")
        self.true_count_var = tk.StringVar(value="True Count: 0.00")
        self.bet_recommendation_var = tk.StringVar(value="Bet Rec: Wait")
        self.action_recommendation_var = tk.StringVar(value="Action Rec: N/A")
        self.ml_prediction_var = tk.StringVar(value="Prediction: Collecting data...")

        self.create_widgets()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queues()

    def create_widgets(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        BG_COLOR = "#FFFACD"
        TEXT_COLOR = "#333333"
        HEADER_COLOR = "#000080"

        self.style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("TLabel", background=BG_COLOR, font=("Segoe UI", 10, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=HEADER_COLOR)
        self.style.configure("TButton", padding=6)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)

        ttk.Label(top_frame, text="Game URL:").pack(side=tk.LEFT, padx=(0, 5))
        url_entry = ttk.Entry(top_frame, textvariable=self.url_var, width=50)
        url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        open_button = ttk.Button(top_frame, text="Open Browser", command=self.open_browser)
        open_button.pack(side=tk.LEFT, padx=5)

        self.track_button = ttk.Button(top_frame, text="Start Tracking", command=self.start_tracking)
        self.track_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(top_frame, text="Stop Tracking", command=self.stop_tracking, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # --- Shoe Controls ---
        shoe_frame = ttk.Frame(main_frame)
        shoe_frame.pack(fill=tk.X, pady=5)
        ttk.Label(shoe_frame, text="Shoe Control:").pack(side=tk.LEFT, padx=(0,10))

        self.shoe_var = tk.StringVar(value="None")
        shoe_names = ["None"] + list(self.shoe_manager.shoes.keys())
        shoe_menu = ttk.OptionMenu(shoe_frame, self.shoe_var, *shoe_names, command=self.on_shoe_select)
        shoe_menu.pack(side=tk.LEFT, padx=5)

        end_shoe_button = ttk.Button(shoe_frame, text="Mark End of Shoe", command=self.mark_end_of_shoe)
        end_shoe_button.pack(side=tk.LEFT, padx=5)

        info_frame = ttk.Frame(main_frame, padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        count_frame = ttk.Frame(info_frame)
        count_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(count_frame, text="Card Counting", style="Header.TLabel").pack(anchor="w")
        ttk.Label(count_frame, textvariable=self.running_count_var).pack(anchor="w")
        ttk.Label(count_frame, textvariable=self.true_count_var).pack(anchor="w")

        strategy_frame = ttk.Frame(info_frame)
        strategy_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(strategy_frame, text="Strategy Assistant", style="Header.TLabel").pack(anchor="w")
        ttk.Label(strategy_frame, textvariable=self.bet_recommendation_var).pack(anchor="w")
        ttk.Label(strategy_frame, textvariable=self.action_recommendation_var).pack(anchor="w")

        # --- ML Prediction Frame ---
        ml_frame = ttk.Frame(info_frame)
        ml_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(ml_frame, text="Advanced Prediction", style="Header.TLabel").pack(anchor="w")
        ttk.Label(ml_frame, textvariable=self.ml_prediction_var).pack(anchor="w")

        display_frame = ttk.Frame(main_frame, padding="10")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(display_frame, text="Live Game Feed").pack(anchor="nw")
        self.display_area = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, state='disabled', font=("Courier New", 11))
        self.display_area.pack(fill=tk.BOTH, expand=True)

    def open_browser(self):
        bat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_chrome.bat")
        if os.path.exists(bat_file):
            try:
                url = self.url_var.get()
                subprocess.Popen([bat_file, url], creationflags=subprocess.CREATE_NEW_CONSOLE)
            except Exception as e:
                print(f"[UI] Error executing .bat file: {e}")
        else:
            print("[UI] Error: restart_chrome.bat not found.")

    def start_tracking(self):
        print("[UI] Starting scraper...")
        # Reset counts and UI when starting a new session
        self.card_counter.reset()
        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None
        self.update_stats_and_strategy(None) # Reset UI labels
        self.display_area.configure(state='normal')
        self.display_area.delete('1.0', tk.END)
        self.display_area.configure(state='disabled')

        self.scraper = Scraper(self.data_queue)
        self.scraper_thread = threading.Thread(target=self.scraper.start, daemon=True)
        self.scraper_thread.start()
        self.track_button.config(state='disabled')
        self.stop_button.config(state='normal')

    def stop_tracking(self):
        if self.scraper:
            self.scraper.stop()
            if self.scraper_thread:
                self.scraper_thread.join(timeout=2)
            self.scraper = None
        self.track_button.config(state='normal')
        self.stop_button.config(state='disabled')

    def process_queues(self):
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                payload = data.get('payloadData', data)
                if not payload or not isinstance(payload, dict):
                    continue

                # --- ML Data Logging ---
                with open("game_data_log.jsonl", "a") as f:
                    f.write(json.dumps(payload) + "\n")

                game_id = payload.get('gameId')
                if not game_id:
                    continue

                if "New Shoe" in str(payload):
                    if self.shoe_manager.active_shoe_name != "None":
                        self.mark_end_of_shoe()
                    else:
                        self.card_counter.reset()
                    self.round_counter = 0
                    self.round_line_map = {}
                    self.update_game_display("--- NEW SHOE DETECTED, COUNTERS RESET ---\n")

                # The shoe manager now correctly identifies only the new cards.
                newly_dealt_cards = self.shoe_manager.process_game_state(payload)

                # The card counter only processes the newly identified cards.
                if newly_dealt_cards:
                    self.card_counter.process_cards(newly_dealt_cards)

                self.update_stats_and_strategy(payload)

                if game_id != self.last_game_id:
                    self.round_counter += 1
                    self.last_game_id = game_id
                    formatted_state = self.format_game_state(payload, self.round_counter)
                    self.update_game_display(formatted_state + "\n")
                    current_line = self.display_area.index(f"end-1c").split('.')[0]
                    self.round_line_map[game_id] = f"{current_line}.0"
                else:
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

    def update_stats_and_strategy(self, payload):
        running_count = self.card_counter.get_running_count()
        true_count = self.card_counter.get_true_count()
        self.running_count_var.set(f"Running Count: {running_count}")
        self.true_count_var.set(f"True Count: {true_count:.2f}")

        bet_rec = get_bet_recommendation(true_count)
        self.bet_recommendation_var.set(f"Bet Rec: {bet_rec}")

        player_hand = []
        dealer_up_card = None

        if payload:
            seats = payload.get('seats', {})
            # Assuming user is in seat 0, or first available seat. This needs to be more robust.
            user_seat = '0'
            if user_seat in seats and seats[user_seat].get('first', {}).get('cards'):
                player_hand = [c['value'] for c in seats[user_seat]['first']['cards']]

            if payload.get('dealer', {}).get('cards'):
                dealer_cards = payload['dealer']['cards']
                if dealer_cards and dealer_cards[0].get('value') != '**':
                    dealer_up_card = dealer_cards[0]['value']

        if player_hand and dealer_up_card:
            action_rec = get_strategy_action(player_hand, dealer_up_card, true_count)
            self.action_recommendation_var.set(f"Action Rec: {action_rec}")
        else:
            self.action_recommendation_var.set("Action Rec: N/A")

        # Placeholder for ML model update
        self.ml_prediction_var.set("Prediction: Analyzing...")


    def format_game_state(self, payload, round_num):
        parts = [f"Round {round_num}:"]
        dealer = payload.get('dealer')
        if dealer:
            cards = ",".join([c.get('value', '?') for c in dealer.get('cards', [])])
            score = dealer.get('score', 'N/A')
            parts.append(f"D:[{cards}]({score})")

        seats = payload.get('seats', {})
        for seat_num in sorted(seats.keys(), key=int):
            hand = seats.get(seat_num, {}).get('first')
            if hand and hand.get('cards'):
                cards = ",".join([c.get('value', '?') for c in hand.get('cards', [])])
                score = hand.get('score', 'N/A')
                state_char = hand.get('state', 'U')[0]
                parts.append(f"S{seat_num}:[{cards}]({score},{state_char})")
        return " | ".join(parts)

    def update_game_display(self, message):
        self.display_area.configure(state='normal')
        self.display_area.insert(tk.END, message)
        self.display_area.configure(state='disabled')
        self.display_area.see(tk.END)

    def on_closing(self):
        self.stop_tracking()
        self.root.destroy()

    def on_shoe_select(self, selected_shoe):
        """Callback for when a new shoe is selected from the dropdown."""
        self.shoe_manager.set_active_shoe(selected_shoe)

        # Reset everything for a clean slate
        self.card_counter.reset()
        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None
        self.update_stats_and_strategy(None)

        self.display_area.configure(state='normal')
        self.display_area.delete('1.0', tk.END)
        self.update_game_display(f"--- Active shoe set to: {selected_shoe} ---\n")
        self.display_area.configure(state='disabled')

    def mark_end_of_shoe(self):
        """Callback for the 'Mark End of Shoe' button."""
        current_shoe_name = self.shoe_manager.active_shoe_name
        if current_shoe_name == "None":
            self.update_game_display("--- No active shoe to end ---\n")
            return

        if self.shoe_manager.end_current_shoe():
            self.update_game_display(f"--- End of {current_shoe_name} Marked & Reshuffled ---\n")
            # For convenience, switch to the other shoe
            next_shoe = "Shoe 2" if current_shoe_name == "Shoe 1" else "Shoe 1"
            self.shoe_var.set(next_shoe)
            self.on_shoe_select(next_shoe)
        else:
            self.update_game_display(f"--- Could not end {current_shoe_name} ---\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
