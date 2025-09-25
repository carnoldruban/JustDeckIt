#!/usr/bin/env python3
"""
browser_refresh_debug.py

An independent script that connects to a Chrome browser running with remote debugging enabled
and periodically refreshes the page to prevent inactivity timeouts in cross-origin iframes.

Usage:
    python browser_refresh_debug.py [--port PORT] [--interval INTERVAL] [--runtime RUNTIME]

Arguments:
    --port: Chrome debugging port (default: 9222)
    --interval: Time between refreshes in minutes (default: 4)
    --runtime: Maximum runtime in hours, 0 for indefinite (default: 0)
"""

import time
import sys
import random
import datetime
import argparse
import traceback
import json

# Force output to be unbuffered
sys.stdout.reconfigure(line_buffering=True)

print("Script starting...")
print(f"Python version: {sys.version}")

try:
    print("Importing selenium...")
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import WebDriverException
    print("Selenium imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import selenium: {e}")
    print("Please install selenium with: pip install selenium")
    sys.exit(1)

try:
    print("Importing webdriver_manager...")
    from webdriver_manager.chrome import ChromeDriverManager
    print("webdriver_manager imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import webdriver_manager: {e}")
    print("Please install webdriver_manager with: pip install webdriver-manager")
    sys.exit(1)

try:
    print("Importing requests...")
    import requests
    print("requests imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import requests: {e}")
    print("Please install requests with: pip install requests")
    sys.exit(1)

print("All imports successful")

class BrowserActivityKeeper:
    def __init__(self, debug_port=9222, refresh_interval=4, max_runtime=0):
        """
        Initialize the activity keeper.
        
        Args:
            debug_port: Chrome debugging port
            refresh_interval: Time between refreshes in minutes
            max_runtime: Maximum runtime in hours (0 for indefinite)
        """
        self.debug_port = debug_port
        self.refresh_interval = refresh_interval * 60  # Convert to seconds
        self.max_runtime = max_runtime * 3600 if max_runtime > 0 else 0  # Convert to seconds
        self.chrome_debug_url = f"http://127.0.0.1:{debug_port}"
        self.driver = None
        self.start_time = time.time()
        self.refresh_count = 0
        
        # Target URL parts to identify relevant tabs
        # Match broadly for OLG and DraftKings anywhere on their domains
        self.target_url_parts = [
            "draftkings.com",
            "olg.ca",
            "evo-games.com"
            # Add more target URLs as needed
        ]
        
        # Initialize logging
        self.log(f"Browser Activity Keeper started")
        self.log(f"Debug port: {debug_port}")
        self.log(f"Refresh interval: {refresh_interval} minutes")
        self.log(f"Max runtime: {max_runtime} hours {'(indefinite)' if max_runtime == 0 else ''}")

    def log(self, message):
        """Log a message with timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        sys.stdout.flush()  # Force flush to ensure output is displayed immediately

    def connect_to_browser(self):
        """Connect to the Chrome browser with remote debugging enabled."""
        self.log(f"Connecting to Chrome at {self.chrome_debug_url}...")
        
        try:
            # First check if we can reach the debugging port
            self.log("Testing connection to Chrome debugging port...")
            response = requests.get(f"{self.chrome_debug_url}/json/version", timeout=5)
            self.log(f"Response status code: {response.status_code}")
            response.raise_for_status()
            
            # Set up Chrome options to connect to the existing debugging session
            self.log("Setting up Chrome options...")
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
            
            # Create a new Chrome driver instance connected to the debugging session
            self.log("Creating Chrome driver instance...")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            self.log("Successfully connected to Chrome browser")
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"Error connecting to Chrome debugging port: {e}")
            self.log(f"Make sure Chrome is running with --remote-debugging-port={self.debug_port}")
            return False
        except Exception as e:
            self.log(f"Unexpected error connecting to Chrome: {e}")
            self.log(traceback.format_exc())
            return False

    def find_target_tab(self):
        """Find and switch to a tab that matches our target URLs using Selenium handles.
        Falls back to CDP if Selenium can't see the correct tab.
        """
        if not self.driver:
            self.log("Driver not initialized, cannot find target tab")
            return False
        
        try:
            # First try via Selenium handles
            self.log("Enumerating Selenium window handles...")
            handles = self.driver.window_handles
            self.log(f"Found {len(handles)} window handles")
            for handle in handles:
                try:
                    self.driver.switch_to.window(handle)
                    url = ""
                    try:
                        url = self.driver.current_url
                    except Exception:
                        url = ""
                    self.log(f"Handle {handle} URL: {url}")
                    if any(part in (url or "") for part in self.target_url_parts):
                        self.log("Switched to target tab via Selenium")
                        return True
                except Exception as e:
                    self.log(f"Error inspecting handle {handle}: {e}")
            
            self.log("No matching tab via Selenium; trying CDP targets list...")
            # Fallback: query Chrome DevTools targets directly
            try:
                resp = requests.get(f"{self.chrome_debug_url}/json", timeout=5)
                resp.raise_for_status()
                targets = resp.json()
                # Prefer page targets (exclude iframes and service workers)
                page_targets = [t for t in targets if t.get('type') == 'page']
                # Find first matching target by URL
                match = None
                for t in page_targets:
                    url = t.get('url') or ''
                    title = t.get('title') or ''
                    self.log(f"Target: type=page title='{title}' url='{url}'")
                    if any(part in url for part in self.target_url_parts):
                        match = t
                        break
                # If no page matched, allow iframe if it matches
                if not match:
                    for t in targets:
                        url = t.get('url') or ''
                        if any(part in url for part in self.target_url_parts):
                            match = t
                            break
                if match:
                    target_id = match.get('id') or match.get('targetId') or match.get('target_id')
                    if target_id:
                        try:
                            # Switch by focusing the target via CDP
                            session = self.driver.session_id
                            self.log(f"Attempting CDP focus on target {target_id} (session {session})")
                            # Selenium 4 supports execute_cdp_cmd
                            self.driver.execute_cdp_cmd('Target.activateTarget', {'targetId': target_id})
                            time.sleep(0.3)
                            # After activation, try to read current url again
                            cur = self.driver.current_url
                            self.log(f"After CDP activation current URL: {cur}")
                            if any(part in (cur or '') for part in self.target_url_parts):
                                self.log("Switched to target tab via CDP")
                                return True
                        except Exception as e:
                            self.log(f"CDP activation failed: {e}")
                else:
                    self.log("No matching target found in CDP list")
            except Exception as e:
                self.log(f"Error querying CDP targets: {e}")
            
            self.log("No matching tab found; staying on current tab")
            return False
        except Exception as e:
            self.log(f"Error finding target tab: {e}")
            self.log(traceback.format_exc())
            return False

    def refresh_page(self):
        """Refresh the current page and wait for readyState=complete."""
        if not self.driver:
            self.log("Driver not initialized, cannot refresh page")
            return False
        
        try:
            current_url = self.driver.current_url
            self.log(f"Refreshing page: {current_url}")
            
            self.driver.refresh()
            
            # Wait for document ready and a short randomized delay
            try:
                for _ in range(20):
                    state = self.driver.execute_script("return document.readyState")
                    if state == "complete":
                        break
                    time.sleep(0.25)
            except Exception:
                pass
            delay = 2 + random.random() * 2
            time.sleep(delay)
            
            new_url = self.driver.current_url
            self.log(f"New URL after refresh: {new_url}")
            # Consider refresh OK if page is not about:blank and did not crash
            if new_url and not new_url.startswith("about:blank"):
                self.log("Page refreshed successfully")
                self.refresh_count += 1
                return True
            else:
                self.log("Page may not have refreshed properly")
                return False
        except WebDriverException as e:
            self.log(f"Error refreshing page: {e}")
            self.log(traceback.format_exc())
            return False

    def refresh_via_cdp(self):
        """Fallback: refresh the matching target using Chrome DevTools Protocol without switching Selenium tab.
        If an iframe for the target domain exists, only that iframe will be reloaded (cross-origin safe).
        """
        try:
            resp = requests.get(f"{self.chrome_debug_url}/json", timeout=5)
            resp.raise_for_status()
            targets = resp.json()
            # Prefer page targets
            candidates = [t for t in targets if t.get('type') == 'page'] or targets
            for t in candidates:
                url = (t.get('url') or '').lower()
                if not any(part.lower() in url for part in self.target_url_parts):
                    continue
                target_id = t.get('id') or t.get('targetId')
                if not target_id:
                    continue
                self.log(f"Refreshing via CDP target {target_id} url={t.get('url')}")
                try:
                    # Attach a temporary session to the page target
                    attach = self.driver.execute_cdp_cmd('Target.attachToTarget', {
                        'targetId': target_id,
                        'flatten': True
                    })
                    session_id = attach.get('sessionId')

                    # 1) Try to find and reload a matching iframe only
                    try:
                        # Get full DOM and pierce shadow DOMs to find iframes
                        doc = self.driver.execute_cdp_cmd('DOM.getDocument', {'depth': -1, 'pierce': True})
                        res = self.driver.execute_cdp_cmd('DOM.querySelectorAll', {
                            'nodeId': doc['root']['nodeId'], 'selector': 'iframe'
                        })
                        node_ids = res.get('nodeIds', [])
                        iframe_refreshed = False
                        for node_id in node_ids:
                            attrs = self.driver.execute_cdp_cmd('DOM.getAttributes', {'nodeId': node_id}).get('attributes', [])
                            attr_map = dict(zip(attrs[0::2], attrs[1::2]))
                            src = (attr_map.get('src') or '').lower()
                            if any(part.lower() in src for part in self.target_url_parts):
                                self.log(f"Reloading iframe via CDP DOM: {src}")
                                # Set same src triggers reload
                                self.driver.execute_cdp_cmd('DOM.setAttributeValue', {
                                    'nodeId': node_id, 'name': 'src', 'value': src
                                })
                                iframe_refreshed = True
                                self.refresh_count += 1
                                break
                        if iframe_refreshed:
                            # Detach and succeed
                            try:
                                self.driver.execute_cdp_cmd('Target.detachFromTarget', {'sessionId': session_id})
                            except Exception:
                                pass
                            self.log("CDP iframe refresh sent successfully")
                            return True
                    except Exception as e_iframe:
                        self.log(f"CDP iframe search/refresh error, will fallback to page reload: {e_iframe}")

                    # 2) Fallback: reload the whole page target
                    self.driver.execute_cdp_cmd('Target.sendMessageToTarget', {
                        'sessionId': session_id,
                        'message': json.dumps({'id': 1, 'method': 'Page.enable'})
                    })
                    self.driver.execute_cdp_cmd('Target.sendMessageToTarget', {
                        'sessionId': session_id,
                        'message': json.dumps({'id': 2, 'method': 'Page.reload', 'params': {'ignoreCache': True}})
                    })
                    # Detach session
                    try:
                        self.driver.execute_cdp_cmd('Target.detachFromTarget', {'sessionId': session_id})
                    except Exception:
                        pass
                    self.refresh_count += 1
                    self.log("CDP page refresh sent successfully (fallback)")
                    return True
                except Exception as e:
                    self.log(f"CDP refresh failed for target {target_id}: {e}")
                    continue
            self.log("No suitable target found for CDP refresh")
            return False
        except Exception as e:
            self.log(f"Error during CDP refresh: {e}")
            return False

    def simulate_activity(self):
        """Simulate some user activity on the page."""
        if not self.driver:
            self.log("Driver not initialized, cannot simulate activity")
            return False
            
        try:
            self.log("Simulating user activity...")
            # Execute JavaScript to simulate mouse movement
            self.driver.execute_script("""
                // Create and dispatch a mouse movement event
                const event = new MouseEvent('mousemove', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: 100 + Math.random() * 500,
                    clientY: 100 + Math.random() * 300
                });
                document.dispatchEvent(event);
                
                // Scroll slightly
                window.scrollBy(0, Math.random() > 0.5 ? 10 : -10);
                
                console.log('[ActivityKeeper] Simulated user activity');
                return "Activity simulated successfully";
            """)
            
            self.log("Simulated user activity on page")
            return True
            
        except Exception as e:
            self.log(f"Error simulating activity: {e}")
            self.log(traceback.format_exc())
            return False

    def check_for_inactivity_popups(self):
        """Check for and dismiss any inactivity popups."""
        if not self.driver:
            self.log("Driver not initialized, cannot check for popups")
            return False
            
        try:
            self.log("Checking for inactivity popups...")
            # Execute JavaScript to find and dismiss inactivity popups
            result = self.driver.execute_script("""
                // Common class names and text for inactivity popups
                const popupSelectors = [
                    '.inactivity-popup', '.timeout-dialog', '.session-timeout',
                    '.modal-dialog', '.popup-container', '.overlay', '.dialog'
                ];
                
                // Common button text for continuing sessions
                const buttonTexts = ['continue', 'resume', 'stay active', 'ok', 'yes', 'dismiss'];
                
                // Check for visible popups
                for (const selector of popupSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const el of elements) {
                        // Check if element is visible
                        if (el.offsetParent !== null) {
                            // Look for buttons within the popup
                            const buttons = el.querySelectorAll('button, .btn, a.button, input[type="button"]');
                            for (const button of buttons) {
                                const text = button.textContent.toLowerCase();
                                if (buttonTexts.some(t => text.includes(t))) {
                                    // Click the button
                                    button.click();
                                    console.log('[ActivityKeeper] Clicked inactivity popup button:', text);
                                    return true;
                                }
                            }
                            
                            // If no specific button found, try clicking the popup itself
                            el.click();
                            console.log('[ActivityKeeper] Clicked inactivity popup element');
                            return true;
                        }
                    }
                }
                
                // Also check for iframes that might contain popups
                const iframes = document.querySelectorAll('iframe');
                if (iframes.length > 0) {
                    console.log('[ActivityKeeper] Found ' + iframes.length + ' iframes, but cannot access cross-origin content');
                }
                
                return false;
            """)
            
            if result:
                self.log("Dismissed inactivity popup")
            else:
                self.log("No inactivity popups found")
            
            return result
            
        except Exception as e:
            self.log(f"Error checking for popups: {e}")
            self.log(traceback.format_exc())
            return False

    def run(self):
        """Run the activity keeper main loop."""
        self.log("Starting main loop...")
        if not self.connect_to_browser():
            self.log("Failed to connect to browser. Exiting.")
            return
        
        if not self.find_target_tab():
            self.log("Failed to find target tab. Will continue and retry.")
        
        last_refresh_time = time.time()
        
        try:
            self.log("Entering main activity loop...")
            last_activity_minute = -1
            while True:
                current_time = time.time()
                elapsed_time = current_time - self.start_time
                time_since_refresh = current_time - last_refresh_time
                current_minute = int(elapsed_time // 60)
                
                # Check if we've exceeded max runtime
                if self.max_runtime > 0 and elapsed_time > self.max_runtime:
                    self.log(f"Reached maximum runtime of {self.max_runtime/3600:.1f} hours. Exiting.")
                    break
                
                # Check for and dismiss any inactivity popups
                self.check_for_inactivity_popups()
                
                # Simulate some activity once per minute
                if current_minute != last_activity_minute and current_minute > 0:
                    self.simulate_activity()
                    last_activity_minute = current_minute
                
                # Refresh the page at the specified interval
                if time_since_refresh >= self.refresh_interval:
                    self.log(f"Time since last refresh: {time_since_refresh/60:.1f} minutes")
                    # Try to find target tab again if needed
                    if not self.find_target_tab():
                        self.log("Target tab not found. Retrying...")
                        # Try CDP refresh as fallback even if we couldn't switch
                        if self.refresh_via_cdp():
                            last_refresh_time = time.time()
                            self.log(f"Next refresh in {self.refresh_interval/60:.1f} minutes (via CDP)")
                            continue
                        time.sleep(10)
                        continue
                    
                    # Refresh the page
                    if self.refresh_page():
                        last_refresh_time = time.time()
                        self.log(f"Next refresh in {self.refresh_interval/60:.1f} minutes")
                
                # Sleep to prevent high CPU usage
                time.sleep(1)
                
                # Print status every hour
                if int(elapsed_time) % 3600 == 0 and int(elapsed_time) > 0:
                    hours_running = elapsed_time / 3600
                    self.log(f"Status: Running for {hours_running:.1f} hours, performed {self.refresh_count} refreshes")
                
        except KeyboardInterrupt:
            self.log("Keyboard interrupt received. Shutting down...")
        except Exception as e:
            self.log(f"Unexpected error: {e}")
            self.log(traceback.format_exc())
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.log("Cleaning up resources...")
        if self.driver:
            try:
                self.log("Closing WebDriver connection")
                self.driver.quit()
            except Exception as e:
                self.log(f"Error closing WebDriver: {e}")
                self.log(traceback.format_exc())
        
        runtime = time.time() - self.start_time
        self.log(f"Browser Activity Keeper stopped after running for {runtime/3600:.2f} hours")
        self.log(f"Performed {self.refresh_count} page refreshes")


def refresh_cross_origin_iframe_once(debug_port: int = 9222, target_domains: list[str] | None = None) -> bool:
    """
    Perform a single cross-origin iframe refresh using Chrome DevTools Protocol.
    - Does NOT fall back to full page reload.
    - Designed to be imported and called from another program.

    Args:
        debug_port: Chrome remote debugging port (default 9222)
        target_domains: List of domain substrings to match inside iframe src and page URL.
                         Defaults to ['draftkings.com', 'olg.ca', 'evo-games.com']

    Returns:
        True if an iframe was found and refreshed; False otherwise.
    """
    # Lazy imports in case this function is imported elsewhere
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception:
        pass  # available at module import time

    import requests

    domains = target_domains or ["draftkings.com", "olg.ca", "evo-games.com"]
    chrome_debug_url = f"http://127.0.0.1:{debug_port}"

    driver = None
    try:
        # Ensure DevTools endpoint is reachable (best-effort)
        try:
            requests.get(f"{chrome_debug_url}/json/version", timeout=3)
        except Exception:
            pass

        # Connect a driver to the existing Chrome via debuggerAddress
        opts = Options()
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

        # Find a matching page target
        resp = requests.get(f"{chrome_debug_url}/json", timeout=5)
        resp.raise_for_status()
        targets = resp.json()
        candidates = [t for t in targets if t.get('type') == 'page'] or targets

        for t in candidates:
            url = (t.get('url') or '').lower()
            if not any(d.lower() in url for d in domains):
                continue
            target_id = t.get('id') or t.get('targetId')
            if not target_id:
                continue

            # Attach and try to reload only the matching iframe(s)
            attach = driver.execute_cdp_cmd('Target.attachToTarget', {'targetId': target_id, 'flatten': True})
            session_id = attach.get('sessionId')
            try:
                doc = driver.execute_cdp_cmd('DOM.getDocument', {'depth': -1, 'pierce': True})
                res = driver.execute_cdp_cmd('DOM.querySelectorAll', {
                    'nodeId': doc['root']['nodeId'], 'selector': 'iframe'
                })
                for node_id in res.get('nodeIds', []):
                    attrs = driver.execute_cdp_cmd('DOM.getAttributes', {'nodeId': node_id}).get('attributes', [])
                    attr_map = dict(zip(attrs[0::2], attrs[1::2]))
                    src = (attr_map.get('src') or '').lower()
                    if any(d.lower() in src for d in domains):
                        # Reset src to trigger reload
                        driver.execute_cdp_cmd('DOM.setAttributeValue', {
                            'nodeId': node_id, 'name': 'src', 'value': src
                        })
                        return True
            finally:
                try:
                    driver.execute_cdp_cmd('Target.detachFromTarget', {'sessionId': session_id})
                except Exception:
                    pass
        return False
    except Exception:
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Keep browser sessions active by refreshing pages periodically.')
    parser.add_argument('--port', type=int, default=9222, help='Chrome debugging port (default: 9222)')
    parser.add_argument('--interval', type=float, default=4, help='Refresh interval in minutes (default: 4)')
    parser.add_argument('--runtime', type=float, default=0, help='Maximum runtime in hours, 0 for indefinite (default: 0)')
    return parser.parse_args()


if __name__ == "__main__":
    print("=" * 60)
    print("BROWSER REFRESH SCRIPT - STARTING")
    print("=" * 60)
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        print(f"Starting with parameters:")
        print(f"  Debug port: {args.port}")
        print(f"  Refresh interval: {args.interval} minutes")
        print(f"  Max runtime: {args.runtime} hours")
        
        # Create and run the activity keeper
        keeper = BrowserActivityKeeper(
            debug_port=args.port,
            refresh_interval=args.interval,
            max_runtime=args.runtime
        )
        keeper.run()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        print(traceback.format_exc())
        print("Script failed to start properly")
    
    print("=" * 60)
    print("BROWSER REFRESH SCRIPT - TERMINATED")
    print("=" * 60)
