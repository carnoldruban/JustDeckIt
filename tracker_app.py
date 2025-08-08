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
        self.last_game_id = None
        self.card_counter = CardCounter(num_decks=8)

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
                subprocess.Popen([bat_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
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
                self.log_message(message)

            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                payload = data.get('payloadData', data)
                if not payload: continue

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

                # --- Display Logic ---
                game_id = payload.get('gameId')
                if game_id and game_id != self.last_game_id:
                    # Check for a "New Shoe" message to reset the counter
                    if "New Shoe" in str(payload): # A simple check
                        self.card_counter.reset()
                        self.log_message("--- NEW SHOE DETECTED, COUNTER RESET ---")
                        self.update_count_labels()

                    self.last_game_id = game_id
                    formatted_state = self.format_game_state(payload)
                    self.log_message(formatted_state)

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queues)

    def format_game_state(self, payload):
        """Formats the raw JSON game data into a readable string."""
        if not payload:
            return "Empty payload received."

        game_id = payload.get('gameId', 'N/A')
        lines = [f"--- Game Round: {game_id} ---"]

        # Format Dealer Info
        dealer = payload.get('dealer')
        if dealer:
            cards = [c.get('value', '?') for c in dealer.get('cards', [])]
            score = dealer.get('score', 'N/A')
            lines.append(f"Dealer: [ {', '.join(cards)} ]  (Score: {score})")

        lines.append("-" * 40)

        # Format Player Info
        seats = payload.get('seats', {})
        for seat_num in sorted(seats.keys(), key=int):
            seat = seats[seat_num]
            # Assumes the main hand is under the 'first' key
            hand = seat.get('first')
            if hand:
                cards = [c.get('value', '?') for c in hand.get('cards', [])]
                score = hand.get('score', 'N/A')
                state = hand.get('state', 'Unknown')
                result = hand.get('result', '')

                line = f"Seat {seat_num}: [ {', '.join(cards)} ] (Score: {score}) - {state}"
                if result:
                    line += f" -> {result}"
                lines.append(line)

        lines.append("=" * 40 + "\n")
        return "\n".join(lines)

    def update_count_labels(self):
        """Updates the running and true count labels in the UI."""
        running_count = self.card_counter.get_running_count()
        true_count = self.card_counter.get_true_count()
        self.running_count_label.config(text=f"Running Count: {running_count}")
        self.true_count_label.config(text=f"True Count: {true_count:.2f}")

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
