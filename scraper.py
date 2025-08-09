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

    async def handle_inactivity_popup(self, websocket, session_id):
        """Periodically checks for and clicks the inactivity popup."""
        request_id_counter = 20000 # Use a different range for these requests

        # Enable the DOM domain
        await websocket.send(json.dumps({"id": request_id_counter, "method": "DOM.enable", "sessionId": session_id}))
        request_id_counter += 1

        while not self.stop_event.is_set():
            try:
                # 1. Get document root
                doc_req_id = request_id_counter
                await websocket.send(json.dumps({"id": doc_req_id, "method": "DOM.getDocument", "sessionId": session_id, "params": {"depth": -1}}))
                request_id_counter += 1

                # 2. Query for the button
                query_req_id = request_id_counter
                # We need the root node ID from the previous call's response, but we can't easily wait for it here.
                # A better approach is to send a script to execute.
                script_req_id = request_id_counter
                await websocket.send(json.dumps({
                    "id": script_req_id,
                    "method": "Runtime.evaluate",
                    "sessionId": session_id,
                    "params": {
                        "expression": "document.querySelector('[data-role=\"play-button\"]')"
                    }
                }))
                request_id_counter += 1

                # In a real application, we'd wait for the response to script_req_id.
                # For this implementation, we will assume if a popup exists, a click at a reasonable
                # location might work, or that we can fire-and-forget a click on the element if found.
                # A more robust solution would be to properly handle the async responses.

                # Let's try to click the button if it exists via a single script.
                click_script = """
                () => {
                    const button = document.querySelector('[data-role="play-button"]');
                    if (button) {
                        button.click();
                        return true; // Indicate that a click was attempted
                    }
                    return false; // Indicate no button was found
                }
                """

                eval_req_id = request_id_counter
                pending_requests[eval_req_id] = "inactivity_check" # Mark this request
                await websocket.send(json.dumps({
                    "id": eval_req_id,
                    "method": "Runtime.evaluate",
                    "sessionId": session_id,
                    "params": {"expression": click_script, "userGesture": True, "returnByValue": True}
                }))
                request_id_counter += 1
                self.log_status("Checking for inactivity popup...")

                await asyncio.sleep(20) # Check every 20 seconds
            except Exception as e:
                self.log_status(f"Popup handler failed: {e}")
                await asyncio.sleep(20) # Wait before retrying

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

                # Run both tasks concurrently
                await asyncio.gather(
                    self.listen_for_game_data(websocket, iframe_session_id),
                    self.handle_inactivity_popup(websocket, iframe_session_id)
                )

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
