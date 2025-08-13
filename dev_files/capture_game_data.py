import asyncio
import json
import requests
import websockets
import time

# --- Configuration ---
CHROME_DEBUG_URL = "http://127.0.0.1:9222"
TARGET_URL_PART = "casino.draftkings.com/games/"
IFRAME_URL_PART = "evo-games.com"
MESSAGE_TO_FIND = "[WS Message] blackjack.v3.game"
OUTPUT_FILE = "game_data.json"
TIMEOUT = 60  # seconds

def get_websocket_url():
    """Fetches the WebSocket debugger URL for the target tab."""
    try:
        response = requests.get(f"{CHROME_DEBUG_URL}/json/list", timeout=5)
        response.raise_for_status()
        targets = response.json()
        for target in targets:
            if TARGET_URL_PART in target.get("url", "") and target.get("type") == "page":
                print(f"✅ Found Target Page: {target.get('title')}")
                return target.get("webSocketDebuggerUrl")
        print("❌ Target page with DraftKings game not found.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to Chrome DevTools: {e}")
        print("💡 Please ensure Chrome is running with '--remote-debugging-port=9222' and the game page is open.")
        return None

async def capture_game_data():
    """Connects to DevTools, finds the game, and captures the data."""
    ws_url = get_websocket_url()
    if not ws_url:
        return

    try:
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as websocket:
            print("✅ Connected to browser's main WebSocket.")

            # Find the iframe target
            await websocket.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
            response_str = await websocket.recv()
            targets = json.loads(response_str).get("result", {}).get("targetInfos", [])

            iframe_target_id = None
            for target in targets:
            # This is the critical fix: Ensure we are attaching to an iframe, not a service_worker.
            if IFRAME_URL_PART in target.get("url", "") and target.get("type") == "iframe":
                    iframe_target_id = target.get("targetId")
                print(f"✅ Found Game Iframe Target: {target.get('title')} (type: {target.get('type')})")
                    break

            if not iframe_target_id:
                print("❌ Game iframe not found. Is the game fully loaded?")
                return

            # Attach to the iframe target
        await websocket.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": iframe_target_id}}))
            response_str = await websocket.recv()
        response_data = json.loads(response_str)
        print(f"🕵️  AttachToTarget Response: {response_data}") # Print the full response for debugging
        iframe_session_id = response_data.get("result", {}).get("sessionId")

            if not iframe_session_id:
                print("❌ Failed to attach to iframe session.")
                return

            print(f"✅ Attached to iframe session: {iframe_session_id}")

            # Enable console API in the iframe session
            await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": iframe_session_id}))

            print("👂 Listening for game data in the iframe console...")
            start_time = time.time()
            request_id_counter = 4 # Start request IDs after the initial ones

            while time.time() - start_time < TIMEOUT:
                try:
                    message_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message = json.loads(message_str)

                    # --- Response to our getProperties request ---
                    if "id" in message and message["id"] >= 4:
                        print("✅ Successfully resolved game data object!")
                        result_properties = message.get("result", {}).get("result", [])
                        game_data = {}
                        for prop in result_properties:
                            name = prop.get("name")
                            value_data = prop.get("value", {})
                            # Simple value extraction
                            if "value" in value_data:
                                game_data[name] = value_data["value"]
                            # For complex objects, just show description for now
                            elif "description" in value_data:
                                game_data[name] = value_data["description"]

                        print("\n--- CAPTURED GAME DATA ---")
                        print(json.dumps(game_data, indent=2))
                        print("--------------------------\n")

                        with open(OUTPUT_FILE, "w") as f:
                            json.dump(game_data, f, indent=4)
                        print(f"💾 Game data saved to {OUTPUT_FILE}")
                        return # Success!

                    # --- Event from the browser ---
                    elif message.get("method") == "Runtime.consoleAPICalled":
                        params = message.get("params", {})
                        args = params.get("args", [])

                        if args and MESSAGE_TO_FIND in args[0].get("value", ""):
                            print(f"🎮 Found '{MESSAGE_TO_FIND}' log group. Looking for the data object...")
                            if len(args) > 1 and args[1].get("objectId"):
                                game_object_id = args[1]["objectId"]
                                print(f"🔎 Found game data objectId: {game_object_id}. Resolving...")

                                # Immediately request its properties
                                current_request_id = request_id_counter
                                request_id_counter += 1
                                await websocket.send(json.dumps({
                                    "id": current_request_id,
                                    "method": "Runtime.getProperties",
                                    "sessionId": iframe_session_id,
                                    "params": {"objectId": game_object_id, "ownProperties": True}
                                }))
                                # The response will be handled by the "id" check above

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error while processing message: {e}")

            print(f"⏰ Timed out after {TIMEOUT} seconds. No complete game data object was captured.")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(capture_game_data())
