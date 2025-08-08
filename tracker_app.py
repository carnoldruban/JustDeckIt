import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import os
import threading
import queue
import json
from scraper import Scraper
from card_counter import CardCounter

class BlackjackTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack Tracker")
        self.root.geometry("800x650") # Increased height for count labels
        self.root.configure(bg="#FFFFE0")

        self.scraper = None
        self.scraper_thread = None
        self.data_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.card_counter = CardCounter(num_decks=8)

        # UI State
        self.round_counter = 0
        self.round_line_map = {} # Maps gameId to a line number in the text widget
        self.last_game_id = None

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#FFFFE0")
        self.style.configure("TLabel", background="#FFFFE0", font=("Arial", 12))
        self.style.configure("TButton",
                             background="#FFFFFF", # White
                             foreground="#000000", # Black text
                             font=("Arial", 12, "bold"),
                             borderwidth=1,
                             relief="solid",
                             padding=5)
        self.style.map("TButton",
                       background=[('active', '#F0F0F0')]) # Lighter grey on hover

        # Main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Top frame for URL and buttons
        self.top_frame = ttk.Frame(self.main_frame)
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

        # Counts Frame
        self.counts_frame = ttk.Frame(self.main_frame)
        self.counts_frame.pack(fill=tk.X, pady=5)

        self.running_count_label = ttk.Label(self.counts_frame, text="Running Count: 0", font=("Arial", 14, "bold"))
        self.running_count_label.pack(side=tk.LEFT, padx=10)

        self.true_count_label = ttk.Label(self.counts_frame, text="True Count: 0.00", font=("Arial", 14, "bold"))
        self.true_count_label.pack(side=tk.LEFT, padx=10)

        self.cards_played_label = ttk.Label(self.counts_frame, text="Cards Played: 0", font=("Arial", 14, "bold"))
        self.cards_played_label.pack(side=tk.LEFT, padx=10)

        self.decks_remaining_label = ttk.Label(self.counts_frame, text="Decks Left: 8.0", font=("Arial", 14, "bold"))
        self.decks_remaining_label.pack(side=tk.LEFT, padx=10)

        # Display Area
        self.display_label = ttk.Label(self.main_frame, text="Live Game Feed")
        self.display_label.pack(fill=tk.X, pady=(10, 2))

        self.display_area = scrolledtext.ScrolledText(self.main_frame, wrap=tk.WORD, font=("Courier New", 11), state='disabled')
        self.display_area.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queues()

    def open_browser(self):
        bat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_chrome.bat")
        if os.path.exists(bat_file):
            self.log_message(f"Executing {bat_file}...")
            try:
                url = self.url_var.get()
                if not url:
                    self.log_message("Error: URL field cannot be empty.")
                    return
                self.log_message(f"Attempting to launch Chrome at: {url}")
                subprocess.Popen([bat_file, url], creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.log_message("Browser launch script started. Please log in and navigate to the game page.")
            except Exception as e:
                self.log_message(f"Error executing .bat file: {e}")
        else:
            self.log_message("Error: restart_chrome.bat not found.")

    def start_tracking(self):
        self.log_message("Starting scraper...")
        self.scraper = Scraper(self.data_queue, self.status_queue)
        self.scraper_thread = threading.Thread(target=self.scraper.start, daemon=True)
        self.scraper_thread.start()

        self.track_button.config(state='disabled')
        self.stop_button.config(state='normal')

    def stop_tracking(self):
        if self.scraper:
            self.log_message("Sending stop signal to scraper...")
            self.scraper.stop()
            self.scraper_thread.join(timeout=2) # Wait a bit for the thread to finish
            self.scraper = None

        self.track_button.config(state='normal')
        self.stop_button.config(state='disabled')

    def process_queues(self):
        try:
            while not self.status_queue.empty():
                message = self.status_queue.get_nowait()
                self.log_message(message + "\n")

            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                payload = data.get('payloadData', data)
                if not payload: continue

                game_id = payload.get('gameId')
                if not game_id: continue

                # --- Card Counting Logic ---
                all_cards = []
                if 'dealer' in payload and 'cards' in payload['dealer']:
                    all_cards.extend([c['value'] for c in payload['dealer']['cards']])
                if 'seats' in payload:
                    for seat in payload['seats'].values():
                        if 'first' in seat and 'cards' in seat['first']:
                            all_cards.extend([c['value'] for c in seat['first']['cards']])
                if self.card_counter.process_cards(all_cards):
                    self.update_count_labels()

                # --- Real-time Display Logic ---
                if game_id != self.last_game_id:
                    self.round_counter += 1
                    self.last_game_id = game_id
                    # If it's a new shoe, reset everything
                    if "New Shoe" in str(payload):
                        self.card_counter.reset()
                        self.log_message("--- NEW SHOE DETECTED, COUNTER RESET ---\n")
                        self.update_count_labels()
                        self.round_counter = 1
                        self.round_line_map = {}

                    # Add a new line for the new round
                    formatted_state = self.format_game_state(payload, self.round_counter)
                    self.log_message(formatted_state + "\n")
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

    def log_message(self, message):
        self.display_area.configure(state='normal')
        self.display_area.insert(tk.END, f"{message}\n")
        self.display_area.configure(state='disabled')
        self.display_area.see(tk.END)

    def on_closing(self):
        self.stop_tracking()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
