from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

def refresh_game_page(debug_port=9222):
    # Set up Chrome options to connect to the existing debugging session
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")

    # Create a new Chrome driver instance connected to the debugging session
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Find the game page and refresh it
    try:
        # Look for the game iframe or page
        iframes = driver.find_elements("tag name", "iframe")
        game_iframe = None
        for iframe in iframes:
            if "evo-games.com" in iframe.get_attribute("src"):
                game_iframe = iframe
                break
        
        if game_iframe:
            print("Found game iframe. Refreshing parent page...")
            driver.refresh()
        else:
            print("Game iframe not found. Refreshing current page...")
            driver.refresh()
        
        time.sleep(5)  # Wait for the page to refresh
        print("Page refreshed successfully.")
    except Exception as e:
        print(f"Error refreshing page: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        try:
            debug_port = int(sys.argv[1])
            refresh_game_page(debug_port)
        except ValueError:
            print("Invalid port number. Using default port 9222.")
            refresh_game_page()
    else:
        refresh_game_page()
