# Blackjack Tracker Application Code

This file contains the current source code for the `scraper.py` and `tracker_app.py` files for review.

## `scraper.py`

```python
import asyncio
import json
import requests
import websockets
import time

class Scraper:
    CHROME_DEBUG_URL = "http://127.0.0.1:9222"
    TARGET_URL_PART = "casino.draftkings.com/games/"
    IFRAME_URL_PART = "evo-games.com"

    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.running = False
        self.ws_url = None
        self.websocket = None
        self.iframe_session_id = None
        self.request_id_counter = 1000

    def start(self):
        self.running = True
        try:
            asyncio.run(self._run())
        except Exception as e:
            print(f"[Scraper] Scraper loop encountered an error: {e}")

    def stop(self):
        print("[Scraper] Stop signal received.")
        self.running = False

    def _get_websocket_url(self):
        print(f"--> [Scraper] STEP 1: Connecting to Chrome at {self.CHROME_DEBUG_URL}...")
        try:
            response = requests.get(f"{self.CHROME_DEBUG_URL}/json/list", timeout=5)
            response.raise_for_status()
            targets = response.json()
            for target in targets:
                if self.TARGET_URL_PART in target.get("url", "") and target.get("type") == "page":
                    print(f"--> [Scraper] STEP 1 - SUCCESS: Found target page: {target.get('title')}")
                    return target.get("webSocketDebuggerUrl")
            print("--> [Scraper] STEP 1 - FAILED: Could not find the DraftKings game tab.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"--> [Scraper] STEP 1 - FAILED: Error connecting to Chrome: {e}")
            return None

    async def _handle_inactivity_popup(self):
        # This is a placeholder for the inactivity handling logic.
        # It can be implemented here if needed.
        pass

    async def _run(self):
        self.ws_url = self._get_websocket_url()
        if not self.ws_url:
            self.running = False
            return

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20) as websocket:
                self.websocket = websocket
                print("--> [Scraper] STEP 2: Connected to browser's main WebSocket.")

                await websocket.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
                msg = await websocket.recv()
                targets = json.loads(msg).get("result", {}).get("targetInfos", [])

                iframe_target_id = None
                for target in targets:
                    if self.IFRAME_URL_PART in target.get("url", "") and target.get("type") == "iframe":
                        iframe_target_id = target.get("targetId")
                        print(f"--> [Scraper] STEP 3: Found game iframe with ID: {iframe_target_id}")
                        break

                if not iframe_target_id:
                    print("--> [Scraper] STEP 3 - FAILED: Game iframe not found.")
                    return

                await websocket.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": iframe_target_id, "flatten": True}}))

                while self.running:
                    msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    msg = json.loads(msg_str)
                    if msg.get("method") == "Target.attachedToTarget":
                        self.iframe_session_id = msg.get("params", {}).get("sessionId")
                        print(f"--> [Scraper] STEP 4 - SUCCESS: Attached to iframe session: {self.iframe_session_id}")
                        await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": self.iframe_session_id}))
                        print("--> [Scraper] STEP 5: Listening for game data...")
                        break

                is_game_message_next = False
                pending_requests = {}

                while self.running:
                    try:
                        msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        msg = json.loads(msg_str)

                        if "id" in msg and msg["id"] in pending_requests:
                            result_value = msg.get("result", {}).get("result", {}).get("value")
                            if result_value:
                                try:
                                    data_obj = json.loads(result_value)
                                    self.data_queue.put(data_obj)
                                except json.JSONDecodeError:
                                    print("[Scraper] FAILED: Could not parse response from browser as JSON.")
                            pending_requests.pop(msg["id"])
                            continue

                        if msg.get("method") == "Runtime.consoleAPICalled" and msg.get("sessionId") == self.iframe_session_id:
                            params = msg.get("params", {})
                            if is_game_message_next and params.get("type") == "log":
                                args = params.get("args", [])
                                if args and args[0].get("type") == "object":
                                    object_id = args[0].get("objectId")
                                    current_request_id = self.request_id_counter
                                    self.request_id_counter += 1
                                    pending_requests[current_request_id] = True
                                    await websocket.send(json.dumps({
                                        "id": current_request_id,
                                        "method": "Runtime.callFunctionOn",
                                        "sessionId": self.iframe_session_id,
                                        "params": {
                                            "functionDeclaration": "function() { return JSON.stringify(this); }",
                                            "objectId": object_id,
                                            "returnByValue": True
                                        }
                                    }))
                                is_game_message_next = False
                            elif params.get("type") == "startGroupCollapsed":
                                args = params.get("args", [])
                                if args and "game" in args[0].get("value", ""):
                                    is_game_message_next = True
                                else:
                                    is_game_message_next = False

                    except asyncio.TimeoutError:
                        await self._handle_inactivity_popup()
                        continue

        except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError) as e:
            print(f"[Scraper] WebSocket connection closed: {e}")
        except Exception as e:
            print(f"[Scraper] An unexpected error occurred in the scraper run loop: {e}")
        finally:
            self.running = False
            print("[Scraper] Scraper has stopped.")

## `tracker_app.py`

```python
import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import os
import threading
import queue
import json
from scraper import Scraper

class BlackjackTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack Tracker - Round Display")
        self.root.geometry("800x600")
        self.root.configure(bg="#FFFACD")

        self.scraper = None
        self.scraper_thread = None
        self.data_queue = queue.Queue()

        self.round_counter = 0
        self.round_line_map = {}
        self.last_game_id = None

        self.create_widgets()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queues()

    def create_widgets(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure(".", background="#FFFACD", foreground="#333333")
        self.style.configure("TFrame", background="#FFFACD")
        self.style.configure("TLabel", background="#FFFACD")
        self.style.configure("TButton", padding=6)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)

        ttk.Label(top_frame, text="Game URL:").pack(side=tk.LEFT, padx=(0, 5))
        self.url_var = tk.StringVar(value="https://casino.draftkings.com")
        url_entry = ttk.Entry(top_frame, textvariable=self.url_var, width=50)
        url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        open_button = ttk.Button(top_frame, text="Open Browser", command=self.open_browser)
        open_button.pack(side=tk.LEFT, padx=5)

        self.track_button = ttk.Button(top_frame, text="Start Tracking", command=self.start_tracking)
        self.track_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(top_frame, text="Stop Tracking", command=self.stop_tracking, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

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

                # The scraper should be putting dictionaries on the queue
                payload = data.get('payloadData', data)
                if not payload or not isinstance(payload, dict):
                    continue

                game_id = payload.get('gameId')
                if not game_id:
                    self.update_game_display(f"RAW: {json.dumps(payload)}\\n")
                    continue

                if game_id != self.last_game_id:
                    self.round_counter += 1
                    self.last_game_id = game_id

                    if "New Shoe" in str(payload):
                        self.update_game_display("--- NEW SHOE DETECTED ---\\n")
                        self.round_counter = 1
                        self.round_line_map = {}

                    formatted_state = self.format_game_state(payload, self.round_counter)
                    self.update_game_display(formatted_state + "\\n")

                    # To allow updates, we need to get the line number
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

if __name__ == "__main__":
    root = tk.Tk()
    app = BlackjackTrackerApp(root)
    root.mainloop()
```
