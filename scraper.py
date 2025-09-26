import asyncio
import json
import websockets
import time
import threading
import requests
import os

# Check for optional dependencies
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    print("[Scraper] Warning: Selenium not available. Browser automation disabled.")
    SELENIUM_AVAILABLE = False

from database_manager import DatabaseManager

class Scraper:
    """
    Connects to a live Chrome instance, scrapes game data, and logs it to the database.
    Also handles refreshing the page to prevent inactivity popups.
    Works with both DraftKings and OLG casino sites (both use Evolution Gaming).
    """
    def __init__(self, db_manager: DatabaseManager, shoe_name: str, shoe_manager=None):
        self.db_manager = db_manager
        self.shoe_manager = shoe_manager
        self.active_shoe_name = shoe_name
        
        self.CHROME_DEBUG_URL = "http://127.0.0.1:9222"
        # Support both DraftKings and OLG casino sites
        self.TARGET_URL_PARTS = [
            "casino.draftkings.com/games/",
            "www.olg.ca/en/casino"
        ]
        self.IFRAME_URL_PART = "evo-games.com"
        
        self.stop_event = threading.Event()
        self.websocket = None
        self.iframe_session_id = None
        self.request_id_counter = 1000
        self.driver = None
        self.last_round_state = None
        self.current_site = None  # Track which site we're connected to

    def get_websocket_url(self):
        print(f"--> [Scraper] Connecting to Chrome at {self.CHROME_DEBUG_URL}...")
        try:
            if not SELENIUM_AVAILABLE:
                print("--> [Scraper] Selenium not available, using requests only.")
                response = requests.get(f"{self.CHROME_DEBUG_URL}/json/list", timeout=5)
                response.raise_for_status()
                targets = response.json()
                for target in targets:
                    if any(part in target.get("url", "") for part in self.TARGET_URL_PARTS):
                        # Detect which site we're connected to
                        url = target.get("url", "")
                        if "draftkings" in url.lower():
                            self.current_site = "DraftKings"
                        elif "olg" in url.lower():
                            self.current_site = "OLG"
                        else:
                            self.current_site = "Unknown Casino"
                        
                        print(f"--> [Scraper] SUCCESS: Found {self.current_site} page: {target.get('title')}")
                        ws = target.get("webSocketDebuggerUrl")
                        if not ws:
                            print("--> [Scraper] FAILED: Target missing webSocketDebuggerUrl. Is Chrome started with --remote-debugging-port=9222?")
                        return ws
                print("--> [Scraper] FAILED: Could not find the DraftKings or OLG game tab.")
                return None
            
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            # The following line automatically downloads and manages the chromedriver
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            response = requests.get(f"{self.CHROME_DEBUG_URL}/json/list", timeout=5)
            response.raise_for_status()
            targets = response.json()
            for target in targets:
                if any(part in target.get("url", "") for part in self.TARGET_URL_PARTS):
                    # Detect which site we're connected to
                    url = target.get("url", "")
                    if "draftkings" in url.lower():
                        self.current_site = "DraftKings"
                    elif "olg" in url.lower():
                        self.current_site = "OLG"
                    else:
                        self.current_site = "Unknown Casino"
                    
                    print(f"--> [Scraper] SUCCESS: Found {self.current_site} page: {target.get('title')}")
                    ws = target.get("webSocketDebuggerUrl")
                    if not ws:
                        print("--> [Scraper] FAILED: Target missing webSocketDebuggerUrl. Is Chrome started with --remote-debugging-port=9222?")
                    return ws
            print("--> [Scraper] FAILED: Could not find the DraftKings or OLG game tab.")
            return None
        except Exception as e:
            print(f"--> [Scraper] FAILED: Error connecting to Chrome: {e}")
            return None

    def get_current_site(self):
        """Returns the current casino site being tracked."""
        return self.current_site or "Not Connected"

    def set_active_shoe(self, shoe_name: str):
        """Updates the active shoe name for logging."""
        self.active_shoe_name = shoe_name

    def _write_full_json(self, data_obj: dict, game_id: str | None):
        """Pretty-print the entire JSON object to a timestamped file for offline analysis."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(base_dir, "data", "raw_payloads")
            os.makedirs(log_dir, exist_ok=True)
            ts = int(time.time() * 1000)
            safe_gid = str(game_id) if game_id else "unknown"
            fname = os.path.join(log_dir, f"payload_{safe_gid}_{ts}.json")
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(data_obj, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Scraper] Warning: could not write raw payload file: {e}")

    def refresh_page(self):
        if self.driver:
            print("[Scraper] Round ended. Refreshing page...")
            self.driver.refresh()
            time.sleep(10) # Give page time to fully reload
            print("[Scraper] Page refreshed.")

    async def run_scraper(self):
        ws_url = self.get_websocket_url()
        if not ws_url:
            return

        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20, max_size=2**24) as websocket:
                self.websocket = websocket
                print("--> [Scraper] Connected to browser's main WebSocket.")

                await websocket.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
                msg = await websocket.recv()
                targets = json.loads(msg).get("result", {}).get("targetInfos", [])

                iframe_target_id = None
                for target in targets:
                    if self.IFRAME_URL_PART in target.get("url", "") and target.get("type") == "iframe":
                        iframe_target_id = target.get("targetId")
                        print(f"--> [Scraper] Found game iframe with ID: {iframe_target_id}")
                        break

                if not iframe_target_id:
                    print("--> [Scraper] Game iframe not found.")
                    return

                await websocket.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": iframe_target_id, "flatten": True}}))

                while not self.stop_event.is_set():
                    msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    msg = json.loads(msg_str)
                    if msg.get("method") == "Target.attachedToTarget":
                        self.iframe_session_id = msg.get("params", {}).get("sessionId")
                        print(f"--> [Scraper] Attached to iframe session: {self.iframe_session_id}")
                        await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": self.iframe_session_id}))
                        print("--> [Scraper] Listening for game data...")
                        break

                is_game_message_next = False
                pending_requests = {}

                while not self.stop_event.is_set():
                    try:
                        msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        msg = json.loads(msg_str)
                        # Reduce noise: only print compact markers
                        if "id" in msg and msg["id"] in pending_requests:
                            result_value = msg.get("result", {}).get("result", {}).get("value")
                            if result_value:
                                try:
                                    data_obj = json.loads(result_value)
                                    payload = data_obj.get('payloadData', data_obj)
                                    # Compact payload marker
                                    gid = payload.get('gameId')
                                    dscore = payload.get('dealer', {}).get('score')
                                    print(f"[Scraper] Parsed payload gameId={gid} dealerScore={dscore}")
                                    # Persist full JSON for offline analysis before storing to DB
                                    try:
                                        self._write_full_json(data_obj, gid)
                                    except Exception as e:
                                        print(f"[Scraper] Raw JSON write error: {e}")
                                    shoe_name = self.shoe_manager.active_shoe_name if self.shoe_manager else self.active_shoe_name
                                    self.db_manager.log_round_update(shoe_name, payload)
                                    
                                    # Process cards through shoe manager for counting
                                    if self.shoe_manager:
                                        self.shoe_manager.process_game_state(payload)
                                    
                                    current_dealer_state = payload.get('dealer', {}).get('state')
                                    if self.last_round_state == "playing" and current_dealer_state != "playing":
                                        self.refresh_page()
                                    self.last_round_state = current_dealer_state
                                except json.JSONDecodeError:
                                    print("[Scraper] Could not parse response from browser as JSON.")
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
                        continue

        except Exception as e:
            print(f"[Scraper] An error occurred: {e}")
        finally:
            self.stop()

    def start(self):
        self.stop_event.clear()
        try:
            asyncio.run(self.run_scraper())
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        print("[Scraper] Stop signal received.")
        self.stop_event.set()
        if self.driver:
            self.driver.quit()
