import asyncio
import json
import requests
import websockets
import time
import threading

class GenericLogDumper:
    def __init__(self, output_file="full_console_log.json"):
        self.output_file = output_file
        self.log_entries = []
        self.stop_event = threading.Event()
        self.CHROME_DEBUG_URL = "http://127.0.0.1:9222"
        self.TARGET_URL_PART = "casino.draftkings.com/games/"
        self.IFRAME_URL_PART = "evo-games.com"

    def log_to_console(self, message):
        """Prints a status message to the console."""
        print(f"[LogDumper] {message}")

    def get_websocket_url(self):
        self.log_to_console("Connecting to Chrome...")
        try:
            response = requests.get(f"{self.CHROME_DEBUG_URL}/json/list", timeout=5)
            response.raise_for_status()
            targets = response.json()
            for target in targets:
                if self.TARGET_URL_PART in target.get("url", "") and target.get("type") == "page":
                    self.log_to_console(f"Found target page: {target.get('title')}")
                    return target.get("webSocketDebuggerUrl")
            self.log_to_console("Could not find the DraftKings game tab.")
            return None
        except requests.exceptions.RequestException as e:
            self.log_to_console(f"Error connecting to Chrome: {e}")
            return None

    async def run_dumper(self):
        ws_url = self.get_websocket_url()
        if not ws_url:
            return

        request_id_counter = 50000
        pending_requests = {}

        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as websocket:
                self.log_to_console("Connected to browser's main WebSocket.")

                # Find and attach to the iframe
                await websocket.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
                msg = await websocket.recv()
                targets = json.loads(msg).get("result", {}).get("targetInfos", [])

                iframe_target_id = None
                for target in targets:
                    if self.IFRAME_URL_PART in target.get("url", "") and target.get("type") == "iframe":
                        iframe_target_id = target.get("targetId")
                        break

                if not iframe_target_id:
                    self.log_to_console("Game iframe not found.")
                    return

                await websocket.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": iframe_target_id, "flatten": True}}))

                iframe_session_id = None
                while not self.stop_event.is_set():
                    msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    msg = json.loads(msg_str)
                    if msg.get("method") == "Target.attachedToTarget":
                        iframe_session_id = msg.get("params", {}).get("sessionId")
                        break

                if not iframe_session_id:
                    self.log_to_console("Could not get session ID after attachment.")
                    return

                await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": iframe_session_id}))
                self.log_to_console("Listening for ALL console logs...")

                while not self.stop_event.is_set():
                    try:
                        msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        msg = json.loads(msg_str)

                        if "id" in msg and msg["id"] in pending_requests:
                            original_log = pending_requests.pop(msg["id"])
                            result_value = msg.get("result", {}).get("result", {}).get("value")
                            original_log["serialized_object"] = result_value
                            self.log_entries.append(original_log)
                            self.log_to_console(f"Captured object for log: {original_log['log_args']}")
                            continue

                        if msg.get("method") == "Runtime.consoleAPICalled" and msg.get("sessionId") == iframe_session_id:
                            log_entry = {
                                "timestamp": time.time(),
                                "event_type": msg["params"]["type"],
                                "log_args": [arg.get("value") for arg in msg["params"]["args"]],
                                "serialized_object": None
                            }

                            # Try to serialize the first object argument
                            if msg["params"]["args"] and msg["params"]["args"][0].get("type") == "object":
                                object_id = msg["params"]["args"][0].get("objectId")
                                if object_id:
                                    req_id = request_id_counter
                                    pending_requests[req_id] = log_entry
                                    await websocket.send(json.dumps({
                                        "id": req_id, "method": "Runtime.callFunctionOn",
                                        "sessionId": iframe_session_id,
                                        "params": {
                                            "functionDeclaration": "function() { return JSON.stringify(this); }",
                                            "objectId": object_id, "returnByValue": True
                                        }
                                    }))
                                    request_id_counter += 1
                                else:
                                    self.log_entries.append(log_entry)
                            else:
                                self.log_entries.append(log_entry)

                    except asyncio.TimeoutError:
                        continue
        except Exception as e:
            self.log_to_console(f"An error occurred: {e}")
        finally:
            self.save_logs()
            self.log_to_console("Dumper has stopped.")

    def save_logs(self):
        self.log_to_console(f"Saving {len(self.log_entries)} log entries to {self.output_file}...")
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.log_entries, f, indent=2)
        self.log_to_console("Save complete.")

    def start(self):
        self.stop_event.clear()
        try:
            asyncio.run(self.run_dumper())
        except KeyboardInterrupt:
            self.log_to_console("Keyboard interrupt received, stopping...")
            self.stop()

    def stop(self):
        self.stop_event.set()

if __name__ == "__main__":
    dumper = GenericLogDumper()
    print("Starting generic log dumper. Press Ctrl+C to stop.")
    dumper.start()