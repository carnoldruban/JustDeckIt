import asyncio
import json
import threading
import time
import websockets

class InactivityHandler:
    """
    A dedicated module to handle the 'GAME PAUSED' inactivity popup.
    It runs in a separate thread and periodically executes a JavaScript
    snippet to find and click the necessary button.
    """
    def __init__(self, websocket, iframe_session_id):
        self.websocket = websocket
        self.iframe_session_id = iframe_session_id
        self.stop_event = threading.Event()
        self.thread = None
        self.request_id_counter = 2000  # Use a different range than the scraper

        # The robust, 3-layered JavaScript for clicking the popup
        self.auto_click_script = """
            () => {
                // Layer 1: Direct, robust search for the main container and button
                const inactivityContainer = document.querySelector('[data-role="inactivity-message-container"]');
                if (inactivityContainer && inactivityContainer.offsetParent !== null) {
                    const playButton = inactivityContainer.querySelector('[data-role="play-button"]');
                    if (playButton) {
                        console.log('[InactivityHandler] Clicking button via Layer 1 (data-role)...');
                        playButton.click();
                        return 'Clicked via Layer 1';
                    }
                }

                // Layer 2: Brute-force search of all buttons' outerHTML
                const allButtons = document.querySelectorAll('button');
                for (const btn of allButtons) {
                    if (btn.outerHTML.includes('data-role="play-button"')) {
                        console.log('[InactivityHandler] Clicking button via Layer 2 (outerHTML)...');
                        btn.click();
                        return 'Clicked via Layer 2';
                    }
                }

                // Layer 3: SVG Path Fingerprinting (very robust)
                const svgPathFingerprint = "M11.5,8.5 L11.5,23.5 L24,16 Z"; // The unique "play" icon path
                const allSvgPaths = document.querySelectorAll('svg > path');
                for (const path of allSvgPaths) {
                    if (path.getAttribute('d') === svgPathFingerprint) {
                        const parentButton = path.closest('button');
                        if (parentButton) {
                            console.log('[InactivityHandler] Clicking button via Layer 3 (SVG Fingerprint)...');
                            parentButton.click();
                            return 'Clicked via Layer 3';
                        }
                    }
                }
                
                return 'No inactivity popup found.';
            }
        """

    async def _run_handler(self):
        """The core async loop that sends the click command."""
        while not self.stop_event.is_set():
            try:
                # Check if websocket is connected and not closed
                if (self.websocket and 
                    self.iframe_session_id and 
                    not self.websocket.closed):
                    
                    await self.websocket.send(json.dumps({
                        "id": self.request_id_counter,
                        "method": "Runtime.evaluate",
                        "sessionId": self.iframe_session_id,
                        "params": {"expression": f"({self.auto_click_script})()"}
                    }))
                    self.request_id_counter += 1
                else:
                    if not self.websocket:
                        print("[InactivityHandler] No WebSocket connection")
                    elif not self.iframe_session_id:
                        print("[InactivityHandler] No iframe session ID")
                    else:
                        print("[InactivityHandler] WebSocket connection closed")
                    break
                    
            except websockets.exceptions.ConnectionClosed:
                print("[InactivityHandler] Connection closed, stopping handler.")
                break
            except Exception as e:
                print(f"[InactivityHandler] Error sending command: {e}")
                break
            
            # Wait for 5 seconds before the next check
            await asyncio.sleep(5)

    def _run_in_new_loop(self):
        """Sets up and runs the asyncio event loop for the handler."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_handler())
        except Exception as e:
            print(f"[InactivityHandler] Error in event loop: {e}")
        finally:
            loop.close()

    def start(self):
        """Starts the inactivity handler in a new background thread."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(
                target=self._run_in_new_loop, 
                name="InactivityHandler",
                daemon=True
            )
            self.thread.start()
            print("[InactivityHandler] Started successfully in a background thread.")
        else:
            print("[InactivityHandler] Handler is already running.")

    def stop(self):
        """Stops the inactivity handler gracefully."""
        print("[InactivityHandler] Stop signal received.")
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                print("[InactivityHandler] Handler thread did not stop gracefully")
        self.thread = None