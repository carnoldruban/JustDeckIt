import asyncio
import json
import requests
import websockets
import time

# --- Configuration ---
CHROME_DEBUG_URL = "http://127.0.0.1:9222"
TARGET_URL_PART = "casino.draftkings.com/games/"
IFRAME_URL_PART = "evo-games.com"
OUTPUT_FILE = "raw_console_events.json"
CAPTURE_DURATION = 30  # seconds

def get_websocket_url():
    """Fetches the WebSocket debugger URL for the target tab."""
    print("\n--- ITERATION 1: Connection & Target Check ---")
    try:
        response = requests.get(f"{CHROME_DEBUG_URL}/json/list", timeout=5)
        response.raise_for_status()
        targets = response.json()
        for target in targets:
            if TARGET_URL_PART in target.get("url", "") and target.get("type") == "page":
                return target.get("webSocketDebuggerUrl")
        print("❌ Target page with DraftKings game not found.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to Chrome DevTools: {e}")
        return None

async def capture_raw_logs():
    """Connects to DevTools, attaches to the iframe, and dumps all events."""
    ws_url = get_websocket_url()
    if not ws_url:
        return

    all_events = []
    try:
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as websocket:
            print("✅ Connected to browser's main WebSocket.")

            # Find and attach to the iframe
            await websocket.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
            response_str = await websocket.recv()
            targets = json.loads(response_str).get("result", {}).get("targetInfos", [])

            iframe_target_id = None
            for target in targets:
                if IFRAME_URL_PART in target.get("url", "") and target.get("type") == "iframe":
                    iframe_target_id = target.get("targetId")
                    break

            if not iframe_target_id:
                print("❌ Game iframe not found.")
                return

            await websocket.send(json.dumps({"id": 2, "method": "Target.attachToTarget", "params": {"targetId": iframe_target_id, "flatten": True}}))
            response_str = await websocket.recv()
            response_data = json.loads(response_str)
            iframe_session_id = response_data.get("result", {}).get("sessionId")

            if not iframe_session_id:
                print("❌ Failed to attach to iframe session.")
                print(f"🕵️  AttachToTarget Response: {response_data}")
                return

            print(f"✅ Attached to iframe session: {iframe_session_id}")

            # Enable Runtime domain to get console logs
            await websocket.send(json.dumps({"id": 3, "method": "Runtime.enable", "sessionId": iframe_session_id}))

            print(f"\n--- ITERATION 3: Raw Event Dump ---")
            print(f"👂 Listening for ALL events from iframe for {CAPTURE_DURATION} seconds...")
            start_time = time.time()

            while time.time() - start_time < CAPTURE_DURATION:
                try:
                    message_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message = json.loads(message_str)

                    # We only care about events from our attached iframe session
                    if message.get("sessionId") == iframe_session_id:
                        print(f"Received event at {time.strftime('%H:%M:%S')}: {message.get('method')}")
                        all_events.append(message)

                except asyncio.TimeoutError:
                    continue

            print(f"\n✅ Capture complete. Captured {len(all_events)} events from the iframe session.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    finally:
        if all_events:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(all_events, f, indent=4)
            print(f"💾 All captured iframe events saved to {OUTPUT_FILE}")
        else:
            print("No events were captured from the iframe session.")

if __name__ == "__main__":
    asyncio.run(capture_raw_logs())
