#!/usr/bin/env python3
"""
Connect to existing Chrome, find iframe, print source, switch to iframe, find second iframe, print source
"""

import re
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

DEFAULT_ALLOWED_HOSTS = [
    r"draftkings\.com",
    r"olg\.ca",
]

IFRAME_URL_PART = "evo-games.com"

def _log(msg: str):
    print(f"[iframe_reader] {msg}", flush=True)

def _connect_driver(debug_port: int) -> webdriver.Chrome:
    """Attach to existing Chrome via remote debugging port."""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def _switch_to_target_tab(driver: webdriver.Chrome) -> bool:
    """Find and switch to casino tab."""
    patterns = []
    for pat in DEFAULT_ALLOWED_HOSTS:
        patterns.append(re.compile(pat, re.IGNORECASE))

    handles = driver.window_handles
    for h in handles:
        try:
            driver.switch_to.window(h)
            url = driver.current_url
            if any(p.search(url) for p in patterns):
                _log(f"Switched to matching tab: {url}")
                return True
        except Exception:
            continue
    return False

def _find_evo_iframe_webelement(driver: webdriver.Chrome):
    """Find Evolution game iframe."""
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        return None

    for iframe in iframes:
        try:
            src = iframe.get_attribute("src") or ""
            src_l = src.lower()
            if IFRAME_URL_PART and IFRAME_URL_PART in src_l:
                _log(f"Identified EVO iframe via src: {src}")
                return iframe
        except Exception:
            continue
    return None

def main():
    driver = _connect_driver(9222)
    _log("Connected to existing Chrome")
    
    if not _switch_to_target_tab(driver):
        _log("No casino tab found")
        return
    
    # Find first iframe
    iframe = _find_evo_iframe_webelement(driver)
    if not iframe:
        _log("No Evolution iframe found")
        return
    
    # Print first iframe source
    print("=== FIRST IFRAME SOURCE ===")
    print(iframe.get_attribute("outerHTML"))
    
    # Switch to first iframe
    driver.switch_to.frame(iframe)
    _log("Switched to first iframe")
    
    # Find second iframe inside first
    second_iframe = _find_evo_iframe_webelement(driver)
    if second_iframe:
        print("=== SECOND IFRAME SOURCE ===")
        print(second_iframe.get_attribute("outerHTML"))
        
        # Switch to second iframe
        driver.switch_to.frame(second_iframe)
        _log("Switched to second iframe")
        
        # Create html_Analysis folder
        if not os.path.exists("html_Analysis"):
            os.makedirs("html_Analysis")
        
        # Capture root div every second
        start_time = time.time()
        counter = 1
        
        try:
            while True:
                try:
                    root_div = driver.find_element(By.ID, "root")
                    div_content = root_div.get_attribute("outerHTML")
                    filename = f"html_Analysis/root_div_{counter}.html"
                    
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(div_content)
                    
                    _log(f"Saved {filename}")
                    counter += 1
                except Exception as e:
                    _log(f"Error capturing root div: {e}")
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            _log("Stopped by user")
        
        _log(f"Captured {counter-1} root div files")
    else:
        _log("No second iframe found")

if __name__ == "__main__":
    main()