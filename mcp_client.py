import json
import websocket
import ssl
import sys
import os
import subprocess
import threading
import queue

class ClineMCPClient:
    def __init__(self):
        self.process = None
        self.message_queue = queue.Queue()
        self.chrome_debug_enabled = False

    def start_mcp_server(self):
        """Start the MCP server process"""
        try:
            # Path to your MCP server
            mcp_server_path = r"C:\Users\User\Documents\Cline\MCP\browser-interaction-server\dist\index.js"

            # Start the MCP server process
            self.process = subprocess.Popen(
                [sys.executable, mcp_server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Start a thread to listen for responses
            threading.Thread(target=self._listen_for_responses, daemon=True).start()

            print("✅ MCP server started successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            return False

    def _listen_for_responses(self):
        """Listen for MCP server responses"""
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                if line.strip():
                    try:
                        response = json.loads(line)
                        self.message_queue.put(response)
                        print(f"🔔 MCP Response: {json.dumps(response, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"📄 MCP Output: {line.strip()}")

    def send_mcp_message(self, message):
        """Send a JSON-RPC message to the MCP server"""
        if self.process and self.process.stdin:
            try:
                json_message = json.dumps(message)
                self.process.stdin.write(json_message + '\n')
                self.process.stdin.flush()

                print(f"📤 Sent to MCP: {json_message}")
                return True
            except Exception as e:
                print(f"❌ Failed to send MCP message: {e}")
                return False
        else:
            print("❌ MCP server not running")
            return False

    def navigate_to_url(self, url):
        """Navigate to a URL using MCP tools"""
        message = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "navigate_to_url",
                "arguments": {
                    "url": url
                }
            },
            "id": 1
        }

        self.send_mcp_message(message)

        # Wait for response
        try:
            response = self.message_queue.get(timeout=10)
            return response
        except queue.Empty:
            print("⏰ No response from MCP server")
            return None

    def stop_server(self):
        """Stop the MCP server"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                print("🛑 MCP server stopped")
            except:
                self.process.kill()
                print("🔫 MCP server forcibly stopped")

    # HTTP/TCP remote connection to MCP server
    def connect_to_mcp_server_remote(self, host='localhost', port=9):
        """Connect to MCP server remotely via HTTP/TCP"""
        try:
            import requests

            # Test the connection
            test_url = f"http://{host}:{port}"
            response = requests.get(test_url, timeout=5)

            if response.status_code == 200:
                self.server_url = test_url
                self.http_port = port
                print(f"✅ Connected to MCP server at {test_url}")
                return True
            else:
                print(f"❌ MCP server returned status {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to MCP server at {host}:{port}")
            return False
        except ImportError:
            print("❌ Requests library not available for HTTP connection")
            return False
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    def call_mcp_tool_http(self, tool_name, arguments=None):
        """Call MCP tool via HTTP"""
        if not self.server_url:
            print("❌ Not connected to MCP server. Call connect_to_mcp_server_remote() first.")
            return None

        try:
            import requests

            message = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                },
                "id": 1
            }

            response = requests.post(self.server_url, json=message, headers={"Content-Type": "application/json"}, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ MCP server error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ HTTP request failed: {e}")
            return None

    # Utility method to connect to Chrome directly for navigation fallback
    def connect_to_chrome_directly(self, url):
        """Connect to Chrome debugging port directly"""
        try:
            import ws
            # Chrome debugging URL (from earlier connection check)
            chrome_url = "ws://localhost:9222/devtools/browser/a39d321b-6f21-4075-a665-7c149f18b90b"

            def send_navigation():
                nav_message = {
                    'id': 1,
                    'method': 'Page.navigate',
                    'params': {'url': url}
                }

                ws_client = websocket.create_connection(chrome_url)
                ws_client.send(json.dumps(nav_message))

                # Get response
                response = json.loads(ws_client.recv())
                print(f"🌐 Chrome Navigation Response: {response}")

                ws_client.close()
                return response

            send_navigation()
            return True

        except ImportError:
            print("❌ WebSocket library not available for direct Chrome connection")
            return False
        except Exception as e:
            print(f"❌ Failed to connect to Chrome directly: {e}")
            return False

# Usage example:
if __name__ == "__main__":
    # This is just for testing the MCP client
    client = ClineMCPClient()

    # Start MCP server
    if client.start_mcp_server():
        # Navigate to Outlier.ai
        result = client.navigate_to_url("https://app.outlier.ai")
        print(f"Navigation result: {result}")

        # Keep running for a bit to see responses
        import time
        time.sleep(5)

    # Stop server
    client.stop_server()
