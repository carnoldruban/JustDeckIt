from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import json

def setup_driver():
    """Setup Chrome driver to connect to the existing debug session."""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    print("🎰 Connecting to existing Chrome instance...")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Successfully connected to Chrome.")
        return driver
    except Exception as e:
        print(f"❌ Error connecting to Chrome: {e}")
        print("💡 Please ensure you have run 'restart_chrome.bat' and Chrome is running.")
        return None

def find_and_switch_to_iframe(driver):
    """Finds and switches to the Evolution Gaming iframe."""
    print("🔍 Looking for the game iframe...")
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute('src') or ''
            if 'evo-games.com' in src:
                driver.switch_to.frame(iframe)
                print("✅ Switched to game iframe.")
                return True
        print("❌ Could not find the Evolution Gaming iframe.")
        return False
    except Exception as e:
        print(f"❌ Error switching to iframe: {e}")
        return False

def inject_interceptor(driver):
    """Injects JavaScript to intercept console logs and capture game data."""
    interceptor_js = """
    (function() {
        if (window.interceptorInjected) {
            console.log('Already injected. Skipping.');
            return '✅ Interceptor was already active.';
        }
        console.log('🎯 Injecting Blackjack data interceptor...');

        window.originalConsoleLog = console.log;
        window.capturedBlackjackObjects = [];
        window.interceptorInjected = true;

        console.log = function(...args) {
            try {
                if (args.length > 0 && typeof args[0] === 'string' && args[0].includes('[WS Message] blackjack.v3.game')) {

                    const gameData = {
                        timestamp: new Date().toISOString(),
                        messageType: args[0],
                        payload: null
                    };

                    if (args.length > 1 && typeof args[1] === 'object' && args[1] !== null) {
                        try {
                            // Deep clone/serialize the object immediately
                            gameData.payload = JSON.parse(JSON.stringify(args[1]));
                            window.capturedBlackjackObjects.push(gameData);
                            window.originalConsoleLog('✅ CAPTURED:', gameData.payload);
                        } catch (e) {
                            window.originalConsoleLog('🔴 Serialization failed:', e);
                        }
                    }
                }
            } catch (e) {
                window.originalConsoleLog('🔴 Error in interceptor:', e);
            }
            window.originalConsoleLog.apply(console, args);
        };

        window.getCapturedData = function() {
            return window.capturedBlackjackObjects;
        };

        return '✅ Interceptor injected successfully.';
    })();
    """
    try:
        result = driver.execute_script(interceptor_js)
        print(f"{result}")
        return True
    except Exception as e:
        print(f"❌ Error injecting interceptor: {e}")
        return False

def main():
    driver = setup_driver()
    if not driver:
        return

    try:
        if not find_and_switch_to_iframe(driver):
            return

        if not inject_interceptor(driver):
            return

        capture_duration = 30
        print(f"👂 Now listening for game data for {capture_duration} seconds... Please play the game.")
        time.sleep(capture_duration)

        print(" Retrieving captured data...")
        captured_data = driver.execute_script("return window.getCapturedData ? window.getCapturedData() : [];")

        if captured_data:
            print(f"✅ Success! Captured {len(captured_data)} game data object(s).")

            with open("final_blackjack_data.json", "w", encoding="utf-8") as f:
                json.dump(captured_data, f, indent=4)
            print("💾 Data saved to final_blackjack_data.json")

            print("\n--- SAMPLE OF CAPTURED DATA ---")
            print(json.dumps(captured_data[0], indent=2))
            print("-----------------------------\n")
        else:
            print("❌ No game data was captured. Please ensure the game is active and dealing hands.")

    except Exception as e:
        print(f"An unexpected error occurred in main loop: {e}")
    finally:
        print("Script finished.")
        # We don't call driver.quit() because we are attaching to an existing session

if __name__ == "__main__":
    main()
