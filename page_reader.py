import requests
import json
import time

class PageReader:
    def __init__(self):
        self.chrome_debug_url = "http://127.0.0.1:9222"
        self.websocket_url = None
        self.session_id = None

    def get_targets(self):
        response = requests.get(f"{self.chrome_debug_url}/json/list", timeout=5)
        targets = response.json()
        for target in targets:
            if target.get("type") == "page":
                self.websocket_url = target.get("webSocketDebuggerUrl")
                print(f"Found page: {target.get('title')}")
                return True
        return False

    def get_page_url(self):
        if not self.websocket_url:
            return None
        import websocket
        import threading

        def on_message(ws, message):
            msg = json.loads(message)
            if msg.get("id") == 1:
                url = msg.get("result", {}).get("frameTree", {}).get("frame", {}).get("url")
                print(f"Current URL: {url}")
                ws.close()

        ws = websocket.WebSocketApp(self.websocket_url, on_message=on_message)
        ws.run_forever()
        return None

    def get_page_text(self):
        if not self.websocket_url:
            return None
        import websocket

        def on_message(ws, message):
            msg = json.loads(message)
            if msg.get("id") == 2:
                result = msg.get("result", {}).get("result", [])
                if result and result[0].get("result"):
                    print("Page text:", result[0]["result"]["value"])
                ws.close()

        ws = websocket.WebSocketApp(self.websocket_url, on_message=on_message)

        # Send command to get page text
        command = {
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.body.textContent"
            }
        }
        ws.send(json.dumps(command))

        ws.run_forever()
        return None

if __name__ == "__main__":
    reader = PageReader()
    while True:
        if reader.get_targets():
            reader.get_page_url()
            reader.get_page_text()
        time.sleep(5)

