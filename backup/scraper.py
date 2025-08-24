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
        """
        Periodically checks for and clicks the "GAME PAUSED" popup.
        """
        if not self.websocket or not self.iframe_session_id:
            return

        js_script = """
            (function() {
                const container = document.querySelector('[data-role="inactivity-message-container"]');
                if (container && container.offsetParent !== null) { // Check if visible
                    const button = container.querySelector('[data-role="play-button"]');
                    if (button) {
                        console.log('Inactivity popup found. Clicking play button.');
                        button.click();
                        return true;
                    }
                }
                return false;
            })();
        """
        try:
            await self.websocket.send(json.dumps({
                "id": self.request_id_counter,
                "method": "Runtime.evaluate",
                "sessionId": self.iframe_session_id,
                "params": {"expression": js_script, "userGesture": True, "awaitPromise": True}
            }))
            self.request_id_counter += 1
        except Exception as e:
            print(f"[Scraper] Error sending inactivity check: {e}")


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
                    try:
                        msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        msg = json.loads(msg_str)
                        if msg.get("method") == "Target.attachedToTarget":
                            self.iframe_session_id = msg.get("params", {}).get("sessionId")
                            print(f"--> [Scraper] STEP 4 - SUCCESS: Attached to iframe session: {self.iframe_session_id}")
                            await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": self.iframe_session_id}))
                            print("--> [Scraper] STEP 5: Listening for game data...")
                            break
                    except asyncio.TimeoutError:
                        continue

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
                        # Instead of just calling it on timeout, let's run it periodically
                        # This is more robust against various timing issues.
                        pass # The check is now part of the main loop body.

                # Periodically check for the inactivity popup, regardless of other messages
                await self._handle_inactivity_popup()
                await asyncio.sleep(5) # Check every 5 seconds

        except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError) as e:
            print(f"[Scraper] WebSocket connection closed: {e}")
        except Exception as e:
            print(f"[Scraper] An unexpected error occurred in the scraper run loop: {e}")
        finally:
            self.running = False
            print("[Scraper] Scraper has stopped.")
