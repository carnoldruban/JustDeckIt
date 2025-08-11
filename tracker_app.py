
import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import os
import threading
import queue
import json
from scraper import Scraper  # Use live scraper
from card_counter import CardCounter
from database_manager import DBManager  # Use live database manager
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
        self.shoe_manager = ShoeManager()
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

    self.BG_COLOR = BG_COLOR
    self.FRAME_BG_COLOR = FRAME_BG_COLOR
    self.BUTTON_BG = BUTTON_BG
    self.BUTTON_ACTIVE_BG = BUTTON_ACTIVE_BG
    self.TEXT_COLOR = TEXT_COLOR
    self.FONT_FAMILY = FONT_FAMILY
    self.FONT_NORMAL = FONT_NORMAL
    self.FONT_BOLD = FONT_BOLD
    self.FONT_HEADER = FONT_HEADER
    self.FONT_MONO = FONT_MONO

    self.style.configure(".", background=self.BG_COLOR, foreground=self.TEXT_COLOR, font=self.FONT_NORMAL)
    self.style.configure("TFrame", background=self.BG_COLOR)
    self.style.configure("TLabel", background=self.BG_COLOR, font=self.FONT_NORMAL)
    self.style.configure("TLabelFrame", background=self.BG_COLOR, font=self.FONT_BOLD)
    self.style.configure("TLabelFrame.Label", background=self.BG_COLOR, font=self.FONT_BOLD)

    self.style.configure("TButton",
                 background=self.BUTTON_BG,
                 foreground=self.TEXT_COLOR,
                 font=self.FONT_BOLD,
                 borderwidth=1,
                 relief="solid",
                 padding=6)
    self.style.map("TButton",
               background=[('active', self.BUTTON_ACTIVE_BG)])

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
        # Removed calls to non-existent methods to prevent AttributeError
    def start_auto_clicker(self):
        import threading
        def click_center_chrome():
            import time
            try:
                import pygetwindow as gw
                import pyautogui
            except ImportError:
                print("pygetwindow and pyautogui are required for auto-clicker.")
                return
            while True:
                try:
                    chrome_windows = [w for w in gw.getWindowsWithTitle('Chrome') if w.isVisible]
                    if chrome_windows:
                        win = chrome_windows[0]
                        center_x = win.left + win.width // 2
                        center_y = win.top + win.height // 2
                        pyautogui.click(center_x, center_y)
                except Exception:
                    pass
                time.sleep(10)
        t = threading.Thread(target=click_center_chrome, daemon=True)
        t.start()

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

    self.zone_analysis_label = ttk.Label(self.zone_analysis_frame, text="Zone analysis requires a tracked shoe.", justify=tk.LEFT, font=self.FONT_MONO)
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

    # ...existing code...

if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
