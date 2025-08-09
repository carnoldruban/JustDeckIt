import asyncio
import json
import requests
import websockets
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

class Scraper:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.stop_event = threading.Event()
        self.driver = None
        self.CHROME_DEBUG_URL = "http://127.0.0.1:9222"
        self.TARGET_URL_PART = "casino.draftkings.com/games/"
        self.IFRAME_URL_PART = "evo-games.com"
        self.ws_listener_thread = None

    def log_status(self, message):
        """Prints a status message to the console."""
        print(f"[Scraper] {message}")

    def get_websocket_url(self):
        self.log_status("Connecting to Chrome...")
        try:
            response = requests.get(f"{self.CHROME_DEBUG_URL}/json/list", timeout=5)
            response.raise_for_status()
            targets = response.json()
            for target in targets:
                if target.get("type") == "page" and self.TARGET_URL_PART in target.get("url", ""):
                    self.log_status(f"Found target page: {target.get('title')}")
                    return target.get("webSocketDebuggerUrl")
            self.log_status("Could not find the DraftKings game tab.")
            return None
        except requests.exceptions.RequestException as e:
            self.log_status(f"Error connecting to Chrome: {e}")
            return None

    def check_for_inactivity_and_click(self):
        """Checks for the inactivity message and clicks the play button if it appears."""
        if not self.driver:
            return
        try:
            # Switch to the iframe to check for the inactivity message
            iframes = self.driver.find_elements("tag name", "iframe")
            for iframe in iframes:
                if self.IFRAME_URL_PART in iframe.get_attribute("src"):
                    self.driver.switch_to.frame(iframe)
                    try:
                        # Check for the inactivity container
                        inactivity_container = self.driver.find_elements("css selector", '[data-role="inactivity-message-container"]')
                        if inactivity_container:
                            self.log_status("Inactivity message detected. Attempting to click 'Play' button.")
                            play_button = self.driver.find_element("css selector", '[data-role="play-button"]')
                            play_button.click()
                            self.log_status("Clicked 'Play' button to resume game.")
                    except NoSuchElementException:
                        # This is expected if the popup is not present
                        pass
                    finally:
                        # Always switch back to the default content
                        self.driver.switch_to.default_content()
                    break # Assuming only one game iframe
        except Exception as e:
            self.log_status(f"Error checking for inactivity: {e}")


    async def listen_for_game_data(self, ws_url):
        """Connects to the websocket and listens for game data."""
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as websocket:
            await websocket.send(json.dumps({"id": 1, "method": "Network.enable"}))
            self.log_status("Network domain enabled. Listening for WebSocket frames...")

            while not self.stop_event.is_set():
                try:
                    message_json = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message = json.loads(message_json)

                    if message.get("method") == "Network.webSocketFrameReceived":
                        payload_data_str = message.get("params", {}).get("response", {}).get("payloadData", "")

                        # Find the start of the JSON data within the payload string
                        json_start_index = payload_data_str.find('[')
                        if json_start_index != -1:
                            try:
                                data_list = json.loads(payload_data_str[json_start_index:])
                                if isinstance(data_list, list) and len(data_list) > 1:
                                    event_name = data_list[0]
                                    event_data = data_list[1]
                                    # Filter for blackjack messages and put them in the queue
                                    if "blackjack.v3" in event_name:
                                        self.data_queue.put(event_data)
                            except json.JSONDecodeError:
                                continue # Ignore payloads that aren't valid JSON

                except asyncio.TimeoutError:
                    continue # No message, continue loop
                except Exception as e:
                    self.log_status(f"Error in WebSocket listener: {e}")
                    break

    def start_ws_listener(self, ws_url):
        """Runs the asyncio event loop in a separate thread."""
        asyncio.run(self.listen_for_game_data(ws_url))

    def start(self):
        self.stop_event.clear()

        # Setup Selenium driver
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            self.driver = webdriver.Chrome(options=chrome_options)
            self.log_status("Selenium connected to existing Chrome instance.")
        except Exception as e:
            self.log_status(f"Failed to connect Selenium to Chrome: {e}")
            return

        # Start WebSocket listener in a background thread
        ws_url = self.get_websocket_url()
        if not ws_url:
            self.log_status("Scraper cannot start. No valid WebSocket URL found.")
            if self.driver:
                self.driver.quit()
            return

        self.ws_listener_thread = threading.Thread(target=self.start_ws_listener, args=(ws_url,), daemon=True)
        self.ws_listener_thread.start()
        self.log_status("WebSocket listener started in background thread.")

        # Main synchronous loop for inactivity checks
        while not self.stop_event.is_set():
            self.check_for_inactivity_and_click()
            time.sleep(10) # Check for inactivity every 10 seconds

        self.log_status("Scraper main loop finished.")


    def stop(self):
        self.stop_event.set()
        if self.ws_listener_thread and self.ws_listener_thread.is_alive():
            self.ws_listener_thread.join(timeout=2)
        if self.driver:
            self.driver.quit()
            self.log_status("Selenium driver quit.")
        self.log_status("Scraper has stopped.")
