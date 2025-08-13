import asyncio
import json
import requests
import websockets
import time

CHROME_DEBUG_URL = "http://127.0.0.1:9222"
TARGET_URL_PART = "casino.draftkings.com/games/"
IFRAME_URL_PART = "evo-games.com"
OUTPUT_FILE = "blackjack_game_data.json"
CAPTURE_DURATION = 30  # seconds

def get_websocket_url():
    """Fetches the WebSocket debugger URL for the target tab."""
    print(f"--> STEP 1: Connecting to Chrome at {CHROME_DEBUG_URL}...")
    try:
        response = requests.get(f"{CHROME_DEBUG_URL}/json/list", timeout=5)
        response.raise_for_status()
        targets = response.json()
        for target in targets:
            if TARGET_URL_PART in target.get("url", "") and target.get("type") == "page":
                print(f"--> STEP 1 - SUCCESS: Found target page: {target.get('title')}")
                return target.get("webSocketDebuggerUrl")
        print("--> STEP 1 - FAILED: Could not find the DraftKings game tab.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"--> STEP 1 - FAILED: Error connecting to Chrome: {e}")
        return None

async def get_and_save_data():
    ws_url = get_websocket_url()
    if not ws_url:
        return

    final_data = []
    request_id_counter = 100  # Start with a high number to not conflict

    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as websocket:
            print("--> STEP 2: Connected to browser's main WebSocket.")

            # Find and attach to the iframe
            await websocket.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
            msg = await websocket.recv()
            targets = json.loads(msg).get("result", {}).get("targetInfos", [])

            iframe_target_id = None
            for target in targets:
                if IFRAME_URL_PART in target.get("url", "") and target.get("type") == "iframe":
                    iframe_target_id = target.get("targetId")
                    print(f"--> STEP 3: Found game iframe with ID: {iframe_target_id}")
                    break

            if not iframe_target_id:
                print("--> STEP 3 - FAILED: Game iframe not found.")
                return

            await websocket.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": iframe_target_id, "flatten": True}}))

            iframe_session_id = None
            while True:
                msg_str = await websocket.recv()
                msg = json.loads(msg_str)
                if msg.get("method") == "Target.attachedToTarget":
                    iframe_session_id = msg.get("params", {}).get("sessionId")
                    print(f"--> STEP 4 - SUCCESS: Attached to iframe session: {iframe_session_id}")
                    break
                if msg.get("id") == 2: continue

            if not iframe_session_id:
                print("--> STEP 4 - FAILED: Could not get session ID after attachment.")
                return

            await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": iframe_session_id}))

            print(f"--> STEP 5: Listening for game data for {CAPTURE_DURATION} seconds...")
            start_time = time.time()

            is_game_message_next = False
            pending_requests = {}

            while time.time() - start_time < CAPTURE_DURATION:
                try:
                    msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    msg = json.loads(msg_str)

                    # This block handles the response from our Runtime.callFunctionOn call
                    if "id" in msg and msg["id"] in pending_requests:
                        print("  - SUCCESS: Received response from browser.")
                        # The result is nested. The actual value is in result.result.value
                        result_value = msg.get("result", {}).get("result", {}).get("value")

                        if result_value:
                            try:
                                # The result_value is a JSON string, parse it
                                full_data_obj = json.loads(result_value)

                                # Now, extract the payloadData key that the user wants
                                payload_content = full_data_obj.get("payloadData")

                                if payload_content:
                                    print("\n--- CAPTURED GAME DATA ---")
                                    print(json.dumps(payload_content, indent=4))
                                    print("--------------------------\n")
                                    # Also save the full object to the file for debugging
                                    final_data.append(full_data_obj)
                                else:
                                    print("  - WARNING: Resolved object, but it has no 'payloadData' key.")

                            except json.JSONDecodeError:
                                print("  - FAILED: Could not parse the response from the browser as JSON.")
                        else:
                            print("  - FAILED: Response from browser did not contain a result value.")

                        # Remove the request from the pending queue
                        pending_requests.pop(msg["id"])
                        continue

                    if msg.get("method") == "Runtime.consoleAPICalled" and msg.get("sessionId") == iframe_session_id:
                        params = msg.get("params", {})

                        if is_game_message_next and params.get("type") == "log":
                            args = params.get("args", [])
                            if args and args[0].get("type") == "object":
                                object_id = args[0].get("objectId")
                                print(f"  - Found the object! ID: {object_id}. Requesting serialization...")

                                current_request_id = request_id_counter
                                request_id_counter += 1

                                # Add to pending requests so we can find the response
                                pending_requests[current_request_id] = True

                                # This is the new method call
                                await websocket.send(json.dumps({
                                    "id": current_request_id,
                                    "method": "Runtime.callFunctionOn",
                                    "sessionId": iframe_session_id,
                                    "params": {
                                        "functionDeclaration": "function() { return JSON.stringify(this); }",
                                        "objectId": object_id,
                                        "returnByValue": True
                                    }
                                }))
                            is_game_message_next = False

                        elif params.get("type") == "startGroupCollapsed":
                            args = params.get("args", [])
                            if args:
                                message_text = args[0].get("value", "")
                                # New, more flexible check for "game" in the title
                                if "game" in message_text:
                                    print(f"Found game-related log group: '{message_text}'")
                                    is_game_message_next = True
                                else:
                                    is_game_message_next = False
                            else:
                                is_game_message_next = False

                except asyncio.TimeoutError:
                    continue

            print(f"\n--> STEP 6: Capture complete.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if final_data:
            print(f"Captured and resolved {len(final_data)} game data object(s).")
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=4)
            print(f"💾 Full game data saved to {OUTPUT_FILE}")
        else:
            print("No 'blackjack.v3.game' messages were captured and resolved.")

if __name__ == "__main__":
    asyncio.run(get_and_save_data())
