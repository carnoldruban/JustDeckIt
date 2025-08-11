import asyncio
import json
import requests
import websockets
import time
import threading

class Scraper:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.stop_event = threading.Event()
        self.CHROME_DEBUG_URL = "http://127.0.0.1:9222"
        self.TARGET_URL_PART = "casino.draftkings.com/games/"
        self.IFRAME_URL_PART = "evo-games.com"

    def log_status(self, message):
        """Prints a status message to the console."""
        print(f"[Scraper] {message}")

    def get_websocket_url(self):
        self.log_status("--> STEP 1: Connecting to Chrome...")
        try:
            response = requests.get(f"{self.CHROME_DEBUG_URL}/json/list", timeout=5)
            response.raise_for_status()
            targets = response.json()
            for target in targets:
                if self.TARGET_URL_PART in target.get("url", "") and target.get("type") == "page":
                    self.log_status(f"--> SUCCESS: Found target page: {target.get('title')}")
                    return target.get("webSocketDebuggerUrl")
            self.log_status("--> FAILED: Could not find the DraftKings game tab.")
            return None
        except requests.exceptions.RequestException as e:
            self.log_status(f"--> FAILED: Error connecting to Chrome: {e}")
            return None

    async def send_inactivity_popup_check(self, websocket, session_id, request_id_counter):
        """Periodically sends inactivity popup check commands (does not call recv)."""
        # Enable the DOM domain once
        await websocket.send(json.dumps({"id": request_id_counter, "method": "DOM.enable", "sessionId": session_id}))
        request_id_counter += 1
        while not self.stop_event.is_set():
            try:
                click_script = """
                () => {
                    // Try to find any visible button with text related to inactivity
                    const keywords = ['continue', 'resume', 'play', 'ok', 'close', 'start', 'back', 'return'];
                    const pauseTexts = ['GAME PAUSED', 'INACTIVITY', 'PAUSED DUE TO INACTIVITY'];
                    let found = false;
                    let buttonText = '';
                    let clicked = false;
                    // First, look for visible buttons with matching text
                    const buttons = Array.from(document.querySelectorAll('button, [role="button"], .clickable'));
                    for (const btn of buttons) {
                        const txt = (btn.textContent || btn.getAttribute('aria-label') || '').toLowerCase();
                        if (btn.offsetParent !== null && keywords.some(k => txt.includes(k))) {
                            btn.click();
                            found = true;
                            buttonText = txt;
                            clicked = true;
                            break;
                        }
                    }
                    // If not found, look for any element with pause text and click nearby button
                    if (!clicked) {
                        const allElements = Array.from(document.querySelectorAll('*'));
                        for (const el of allElements) {
                            const txt = (el.textContent || '').toLowerCase();
                            if (pauseTexts.some(pt => txt.includes(pt.toLowerCase()))) {
                                const parent = el.parentElement;
                                if (parent) {
                                    const btns = parent.querySelectorAll('button, [role="button"], .clickable');
                                    for (const btn of btns) {
                                        if (btn.offsetParent !== null) {
                                            btn.click();
                                            found = true;
                                            buttonText = btn.textContent || btn.getAttribute('aria-label') || 'pause popup';
                                            clicked = true;
                                            break;
                                        }
                                    }
                                }
                            }
                            if (clicked) break;
                        }
                    }
                    // Log all visible buttons for debugging
                    let visibleButtons = [];
                    for (const btn of buttons) {
                        if (btn.offsetParent !== null) {
                            visibleButtons.push(btn.textContent || btn.getAttribute('aria-label') || '');
                        }
                    }
                    return { found, buttonText, visibleButtons };
                }
                """
                eval_req_id = request_id_counter
                request_id_counter += 1
                await websocket.send(json.dumps({
                    "id": eval_req_id,
                    "method": "Runtime.evaluate",
                    "sessionId": session_id,
                    "params": {"expression": click_script, "userGesture": True, "returnByValue": True}
                }))
                await asyncio.sleep(15)
            except Exception as e:
                self.log_status(f"Popup handler send failed: {e}")
                await asyncio.sleep(15)

    async def listen_for_game_data(self, websocket, session_id):
        """The main loop for listening to and processing game data events."""
        request_id_counter = 100
        pending_requests = {}
        is_game_message_next = False

        while not self.stop_event.is_set():
            try:
                msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                msg = json.loads(msg_str)

                if "id" in msg and msg["id"] in pending_requests:
                    request_type = pending_requests.pop(msg["id"])
                    if request_type == "inactivity_check":
                        result = msg.get("result", {}).get("result", {})
                        self.log_status(f"Inactivity check result: {result.get('value')}")
                    else: # Assumes it's a game data request
                        self.log_status("  - SUCCESS: Received game data response from browser.")
                        result_value = msg.get("result", {}).get("result", {}).get("value")
                        if result_value:
                            try:
                                full_data_obj = json.loads(result_value)
                                self.data_queue.put(full_data_obj)
                            except json.JSONDecodeError:
                                self.log_status("  - FAILED: Could not parse response as JSON.")
                        else:
                            self.log_status("  - FAILED: Response did not contain a result value.")
                    continue

                if msg.get("method") == "Runtime.consoleAPICalled" and msg.get("sessionId") == session_id:
                    params = msg.get("params", {})
                    if is_game_message_next and params.get("type") == "log":
                        args = params.get("args", [])
                        if args and args[0].get("type") == "object":
                            object_id = args[0].get("objectId")
                            self.log_status(f"  - Found game object! ID: {object_id}. Requesting data...")

                            current_request_id = request_id_counter
                            request_id_counter += 1
                            pending_requests[current_request_id] = "game_data"

                            await websocket.send(json.dumps({
                                "id": current_request_id, "method": "Runtime.callFunctionOn",
                                "sessionId": session_id,
                                "params": {
                                    "functionDeclaration": "function() { return JSON.stringify(this); }",
                                    "objectId": object_id, "returnByValue": True
                                }
                            }))
                        is_game_message_next = False

                    elif params.get("type") == "startGroupCollapsed":
                        args = params.get("args", [])
                        if args and "game" in args[0].get("value", ""):
                            self.log_status(f"Found game-related log group: '{args[0].get('value', '')}'")
                            is_game_message_next = True
                        else:
                            is_game_message_next = False
            except asyncio.TimeoutError:
                continue

    async def run_scraper(self):
        ws_url = self.get_websocket_url()
        if not ws_url:
            self.log_status("Scraper cannot start. No valid WebSocket URL found.")
            return

        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as websocket:
                self.log_status("--> STEP 2: Connected to browser's main WebSocket.")

                await websocket.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
                msg = await websocket.recv()
                targets = json.loads(msg).get("result", {}).get("targetInfos", [])

                iframe_target_id = None
                for target in targets:
                    if self.IFRAME_URL_PART in target.get("url", "") and target.get("type") == "iframe":
                        iframe_target_id = target.get("targetId")
                        self.log_status(f"--> STEP 3: Found game iframe with ID: {iframe_target_id}")
                        break

                if not iframe_target_id:
                    self.log_status("--> FAILED: Game iframe not found.")
                    return

                await websocket.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": iframe_target_id, "flatten": True}}))

                iframe_session_id = None
                while not self.stop_event.is_set():
                    try:
                        msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        msg = json.loads(msg_str)
                        if msg.get("method") == "Target.attachedToTarget":
                            iframe_session_id = msg.get("params", {}).get("sessionId")
                            self.log_status(f"--> STEP 4: SUCCESS: Attached to iframe session: {iframe_session_id}")
                            break
                    except asyncio.TimeoutError:
                        continue

                if not iframe_session_id:
                    self.log_status("--> FAILED: Could not get session ID after attachment.")
                    return

                await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": iframe_session_id}))
                self.log_status("--> STEP 5: Starting data listener and keep-alive tasks...")

                # Start periodic inactivity popup check sender
                request_id_counter = 20000
                asyncio.create_task(self.send_inactivity_popup_check(websocket, iframe_session_id, request_id_counter))

                # Main message loop: only this coroutine calls recv
                request_id_counter_game = 100
                pending_requests = {}
                is_game_message_next = False
                while not self.stop_event.is_set():
                    try:
                        msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        msg = json.loads(msg_str)

                        # Handle inactivity popup responses
                        if "id" in msg and msg["id"] >= 20000:
                            result = msg.get("result", {}).get("result", {}).get("value", {})
                            if result.get("found"):
                                self.log_status(f"✓ Inactivity popup handled: {result.get('buttonText', 'Unknown button')}")
                            continue

                        # Handle game data responses
                        if "id" in msg and msg["id"] in pending_requests:
                            request_type = pending_requests.pop(msg["id"])
                            if request_type == "game_data":
                                self.log_status("  - SUCCESS: Received game data response from browser.")
                                result_value = msg.get("result", {}).get("result", {}).get("value")
                                if result_value:
                                    try:
                                        full_data_obj = json.loads(result_value)
                                        self.data_queue.put(full_data_obj)
                                    except json.JSONDecodeError:
                                        self.log_status("  - FAILED: Could not parse response as JSON.")
                                else:
                                    self.log_status("  - FAILED: Response did not contain a result value.")
                            continue

                        # Handle game-related log events
                        if msg.get("method") == "Runtime.consoleAPICalled" and msg.get("sessionId") == iframe_session_id:
                            params = msg.get("params", {})
                            if is_game_message_next and params.get("type") == "log":
                                args = params.get("args", [])
                                if args and args[0].get("type") == "object":
                                    object_id = args[0].get("objectId")
                                    self.log_status(f"  - Found game object! ID: {object_id}. Requesting data...")

                                    current_request_id = request_id_counter_game
                                    request_id_counter_game += 1
                                    pending_requests[current_request_id] = "game_data"

                                    await websocket.send(json.dumps({
                                        "id": current_request_id, "method": "Runtime.callFunctionOn",
                                        "sessionId": iframe_session_id,
                                        "params": {
                                            "functionDeclaration": "function() { return JSON.stringify(this); }",
                                            "objectId": object_id, "returnByValue": True
                                        }
                                    }))
                                is_game_message_next = False

                            elif params.get("type") == "startGroupCollapsed":
                                args = params.get("args", [])
                                if args and "game" in args[0].get("value", ""):
                                    self.log_status(f"Found game-related log group: '{args[0].get('value', '')}'")
                                    is_game_message_next = True
                                else:
                                    is_game_message_next = False
                    except asyncio.TimeoutError:
                        continue

        except Exception as e:
            self.log_status(f"An error occurred in the scraper: {e}")
        finally:
            self.log_status("Scraper has stopped.")

    def start(self):
        # This will be called from the GUI thread
        self.stop_event.clear()
        asyncio.run(self.run_scraper())

    def stop(self):
        # This will be called from the GUI thread
        self.stop_event.set()
        self.log_status("Stop signal sent to scraper.")