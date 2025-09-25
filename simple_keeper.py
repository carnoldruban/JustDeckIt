import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("=== SIMPLE BROWSER KEEPER ===")

def keep_browser_alive(port=9222, interval=240):
    driver = None
    try:
        print("Setting up Chrome options...")
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        
        # Add these options for better stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        print("Initializing WebDriver...")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            print("Make sure Chrome is running with: --remote-debugging-port=9222")
            return

        print(f"Connected to Chrome on port {port}")
        print(f"Will refresh every {interval} seconds")
        print("Press Ctrl+C to stop")
        
        while True:
            try:
                print(f"\nRefreshing at {time.strftime('%H:%M:%S')}...")
                driver.refresh()
                time.sleep(2)  # Wait for page to start loading
                # Wait for page to be interactive
                driver.execute_script("return document.readyState") == "complete"
                time.sleep(interval - 2)
            except KeyboardInterrupt:
                print("\nStopping...")
                break
            except Exception as e:
                print(f"Error during refresh: {e}")
                time.sleep(5)  # Wait before retrying
                
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                print("WebDriver closed successfully")
            except:
                pass

if __name__ == "__main__":
    keep_browser_alive(port=9222, interval=240)