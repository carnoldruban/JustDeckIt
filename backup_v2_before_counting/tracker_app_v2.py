import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import os
import threading
import queue
import json
from scraper import Scraper
from shoe_manager import ShoeManager
from card_counter import CardCounter
import shoe

class BlackjackTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack Tracker")
        self.root.geometry("1200x700")

        self.scraper = None
        self.scraper_thread = None
        self.data_queue = queue.Queue()
        self.shoe_manager = ShoeManager()
        self.shoe_manager.set_active_shoe("Shoe 1")
        self.card_counter = CardCounter()

        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None

        self.create_widgets()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queues()

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
        self.active_shoe_var = tk.StringVar(value=self.shoe_manager.active_shoe_name)
        ttk.Label(shoe_controls_frame, textvariable=self.active_shoe_var, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)

        self.end_shoe_button = ttk.Button(shoe_controls_frame, text="Mark End of Shoe / Switch & Shuffle", command=self.handle_shoe_end)
        self.end_shoe_button.pack(side=tk.LEFT, padx=10)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        live_tracker_tab = ttk.Frame(notebook, padding="10")
        shuffle_tracking_tab = ttk.Frame(notebook, padding="10")

        notebook.add(live_tracker_tab, text="Live Tracker")
        notebook.add(shuffle_tracking_tab, text="Shoe & Shuffle Tracking")

        live_left_frame = ttk.Frame(live_tracker_tab)
        live_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        live_right_frame = ttk.Frame(live_tracker_tab)
        live_right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

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
        if os.path.exists(bat_file): subprocess.Popen([bat_file], creationflags=subprocess.CREATE_NEW_CONSOLE)

    def start_tracking(self):
        self.data_queue = queue.Queue()
        self.scraper = Scraper(self.data_queue)
        self.scraper_thread = threading.Thread(target=self.scraper.start, daemon=True)
        self.scraper_thread.start()
        self.track_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.update_game_display("--- Tracking Started ---\n")
        self.update_zone_display()

    def stop_tracking(self):
        if self.scraper: self.scraper.stop()
        self.track_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.update_game_display("--- Tracking Stopped ---\n")

    def process_queues(self):
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                payload = data.get('payloadData', data)
                if not payload or not isinstance(payload, dict): continue

                newly_dealt_cards = self.shoe_manager.process_game_state(payload)

                game_id = payload.get('gameId')
                if not game_id:
                    self.update_game_display(f"RAW: {json.dumps(payload)}\n")
                    continue

                if game_id != self.last_game_id:
                    self.round_counter += 1
                    self.last_game_id = game_id
                    if "New Shoe" in str(payload):
                        self.update_game_display("--- NEW SHOE DETECTED ---\n")
                        self.round_counter = 1
                        self.round_line_map = {}
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

                self.update_zone_display()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queues)

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

    def handle_shoe_end(self):
        try:
            shuffle_params = {"zones": int(self.zones_var.get()), "chunks": int(self.chunks_var.get()), "iterations": int(self.iterations_var.get())}
        except ValueError:
            return
        if self.shoe_manager.end_current_shoe_and_shuffle(shuffle_params):
            current_shoe = self.shoe_manager.active_shoe_name
            next_shoe = "Shoe 2" if current_shoe == "Shoe 1" else "Shoe 1"
            self.shoe_manager.set_active_shoe(next_shoe)
            self.active_shoe_var.set(next_shoe)
            self.display_area.configure(state='normal')
            self.display_area.delete('1.0', tk.END)
            self.update_game_display(f"--- Switched to {next_shoe}. Previous shoe is shuffling. ---\n")
            self.display_area.configure(state='disabled')
            self.update_zone_display()
        else:
            print("[UI] Could not start shuffle.")

    def on_closing(self):
        self.stop_tracking()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
