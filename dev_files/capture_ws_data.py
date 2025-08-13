import asyncio
import json
import websockets
import requests
from pprint import pprint

async def capture_ws_data():
    """
    Connects to the Chrome DevTools Protocol WebSocket and captures
    live blackjack game data from WebSocket messages.
    """
    print("--- Blackjack WebSocket Data Capture ---")

    # Get the WebSocket debugger URL from the Chrome DevTools endpoint
    try:
        response = requests.get("http://127.0.0.1:9222/json/version")
        response.raise_for_status()
        ws_url = response.json().get("webSocketDebuggerUrl")
        if not ws_url:
            print("❌ Could not find WebSocket debugger URL. Is Chrome running with --remote-debugging-port=9222?")
            return
        print(f"✅ Found Chrome DevTools WebSocket URL: {ws_url}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection to Chrome failed. Please ensure Chrome is running with the --remote-debugging-port=9222 flag.")
        return

    async with websockets.connect(ws_url) as websocket:
        # Enable Network domain to receive WebSocket events
        await websocket.send(json.dumps({"id": 1, "method": "Network.enable"}))
        print("✅ Network domain enabled. Listening for WebSocket frames...")

        start_time = asyncio.get_event_loop().time()
        duration = 60  # Run for 60 seconds

        while asyncio.get_event_loop().time() - start_time < duration:
            try:
                message_json = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                message = json.loads(message_json)

                # Check for WebSocket frame received events
                if message.get("method") == "Network.webSocketFrameReceived":
                    payload_data = message.get("params", {}).get("response", {}).get("payloadData")
                    if "blackjack.v3" in payload_data:
                        print("\n--- 🎰 Captured Blackjack Game Data ---")
                        try:
                            # The payload is often a stringified JSON with a prefix, e.g., "42[\"...", so we find the start of the JSON
                            json_start_index = payload_data.find('{')
                            if json_start_index != -1:
                                game_json_str = payload_data[json_start_index:]
                                game_data = json.loads(game_json_str)
                                pprint(game_data)

                                # Save to file
                                with open("blackjack_game_data.json", "a") as f:
                                    json.dump(game_data, f, indent=2)
                                    f.write('\n')

                        except json.JSONDecodeError:
                            print("📦 Raw Payload (not valid JSON):", payload_data)
                        except Exception as e:
                            print(f"❗️ Error processing payload: {e}")

            except asyncio.TimeoutError:
                continue # No message received, continue waiting
            except Exception as e:
                print(f"❗️ An error occurred: {e}")
                break

    print("\n--- ✅ Capture complete. Data saved to blackjack_game_data.json ---")

if __name__ == "__main__":
    # Ensure an event loop is running
    try:
        asyncio.run(capture_ws_data())
    except KeyboardInterrupt:
        print("\nScript manually stopped.")
