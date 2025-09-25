#!/usr/bin/env python3
"""
Inactivity Bypass & Watchdog (Chrome CDP attach via remote debugging)

Features:
- Attaches to already-open Chrome (started with --remote-debugging-port=9222)
- Finds the OLG/DraftKings tab and the Evolution iframe (evo-games.com)
- Dismisses inactivity overlay inside iframe (clicks play button/clickable area)
- Detects top-level "SESSION EXPIRED" popup and refreshes the page
- Falls back to full page refresh when needed
- Provides refresh_once() and a fast watchdog loop (every 3s) run_watchdog()

Example Chrome launch:
"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 "https://casino.draftkings.com"

CLI:
- Single pass:           python inactivity_bypass.py [port] [host_hint]
- Continuous watchdog:   python inactivity_bypass.py [port] [host_hint] --loop [interval_sec]
  Defaults: port=9222, interval=3 seconds

Importable API:
- from inactivity_bypass import refresh_once, run_watchdog
- ok = refresh_once(debug_port=9222, host_hint="(olg|draftkings)")
- run_watchdog(debug_port=9222, host_hint="(olg|draftkings)", interval_sec=3)
"""

import re
import sys
import time
from typing import Optional, Tuple, List, Dict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DEFAULT_ALLOWED_HOSTS = [
    r"draftkings\.com",
    r"olg\.ca",
]

EVO_HOST_HINTS = [
    "evo",                # general
    "evo-games",          # common
    "evolution",          # sometimes appears
    "evolutiongaming",    # sometimes appears
]

# Explicit URL part hint (from user): target evo iframe src contains this
IFRAME_URL_PART = "evo-games.com"


def _log(msg: str):
    print(f"[inactivity_bypass] {msg}", flush=True)


def _connect_driver(debug_port: int) -> webdriver.Chrome:
    """Attach to an existing Chrome via remote debugging port."""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def _switch_to_target_tab(driver: webdriver.Chrome, host_hint_regex: Optional[str]) -> bool:
    """
    Iterate all window handles and focus the first one that matches host_hint_regex or DEFAULT_ALLOWED_HOSTS.
    Returns True if a matching tab was focused.
    """
    patterns = []
    if host_hint_regex:
        patterns.append(re.compile(host_hint_regex, re.IGNORECASE))
    for pat in DEFAULT_ALLOWED_HOSTS:
        patterns.append(re.compile(pat, re.IGNORECASE))

    try:
        current = driver.current_window_handle
    except Exception:
        return False

    handles = driver.window_handles

    # Try current first (fast path)
    try:
        url = driver.current_url
        if any(p.search(url) for p in patterns):
            _log(f"Using current tab: {url}")
            return True
    except Exception:
        pass

    for h in handles:
        try:
            driver.switch_to.window(h)
            url = driver.current_url
            if any(p.search(url) for p in patterns):
                _log(f"Switched to matching tab: {url}")
                return True
        except WebDriverException:
            continue

    # Revert to original if no match found
    try:
        driver.switch_to.window(current)
    except Exception:
        pass
    return False


def _find_evo_iframe_webelement(driver: webdriver.Chrome) -> Optional[object]:
    """
    Try to locate the Evolution game iframe by scanning top-level iframe src attributes.
    Returns a WebElement or None.
    """
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        return None

    for iframe in iframes:
        try:
            src = iframe.get_attribute("src") or ""
            src_l = src.lower()
            if (IFRAME_URL_PART and IFRAME_URL_PART in src_l) or any(h in src_l for h in EVO_HOST_HINTS):
                _log(f"Identified EVO iframe via src: {src}")
                return iframe
        except Exception:
            continue
    return None




def _cdp_get_frame_tree(driver: webdriver.Chrome) -> Dict:
    return driver.execute_cdp_cmd("Page.getFrameTree", {})


def _collect_frames(tree: Dict) -> List[Dict]:
    """Flatten frameTree into list of frames with their 'frame' dict."""
    result = []

    def walk(node):
        if not node:
            return
        frame = node.get("frame")
        if frame:
            result.append(frame)
        children = node.get("childFrames") or node.get("children") or []
        for child in children:
            walk(child)

    walk(tree.get("frameTree", {}))
    return result


def _refresh_if_expired(driver: webdriver.Chrome) -> bool:
    """
    Detect 'SESSION EXPIRED' popup in top document and refresh full page if present.
    Returns True if a full refresh was triggered.
    """
    try:
        candidates = driver.find_elements(By.CSS_SELECTOR, "[data-role='popup'][data-popup-id='inactivity'] [data-role='title']")
        for el in candidates:
            try:
                text = (el.text or "").strip().upper()
                if "SESSION EXPIRED" in text:
                    _log("Detected SESSION EXPIRED popup. Refreshing entire page...")
                    driver.refresh()
                    try:
                        WebDriverWait(driver, 3).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    except Exception:
                        pass
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _refresh_iframe_via_cdp(driver: webdriver.Chrome, evo_url_hint_substr: Optional[str]) -> bool:
    """
    Use CDP to find the evo iframe by URL and then reload only that frame via an isolated world.
    Returns True if CDP refresh was attempted.
    """
    try:
        ftree = _cdp_get_frame_tree(driver)
        frames = _collect_frames(ftree)
        target_frame_id = None
        chosen_url = None

        # Prefer URL hint if provided
        for fr in frames:
            url = (fr.get("url") or "").lower()
            if evo_url_hint_substr and evo_url_hint_substr in url:
                target_frame_id = fr.get("id") or fr.get("frameId") or fr.get("frame", {}).get("id")
                chosen_url = url
                break

        # Else match by 'evo' hints
        if not target_frame_id:
            for fr in frames:
                url = (fr.get("url") or "").lower()
                if any(h in url for h in EVO_HOST_HINTS):
                    target_frame_id = fr.get("id") or fr.get("frameId") or fr.get("frame", {}).get("id")
                    chosen_url = url
                    break

        if not target_frame_id:
            _log("CDP: No evo frameId found in frame tree.")
            return False

        _log(f"CDP: Found evo frameId={target_frame_id} url={chosen_url}")

        # Create an isolated world in that frame
        iw = driver.execute_cdp_cmd("Page.createIsolatedWorld", {
            "frameId": target_frame_id,
            "worldName": "evo_reload_world",
            "grantUniveralAccess": True  # harmless param
        })

        context_id = iw.get("executionContextId")
        if not context_id:
            _log("CDP: Failed to create isolated world for evo frame.")
            return False

        # Reload only the iframe
        driver.execute_cdp_cmd("Runtime.evaluate", {
            "contextId": context_id,
            "expression": "window.location.reload();",
            "awaitPromise": False,
            "returnByValue": True,
        })

        _log("CDP: Issued window.location.reload() inside evo iframe.")
        return True

    except Exception as e:
        _log(f"CDP: Exception while refreshing iframe: {e}")
        return False


def _try_dismiss_inactivity_buttons(driver: webdriver.Chrome, iframe_el, timeout_sec: int = 3) -> bool:
    """
    Switch into the evo iframe and attempt to click common inactivity overlay buttons.
    Returns True if a click was performed.
    """
    try:
        driver.switch_to.frame(iframe_el)
    except Exception:
        return False

    # CSS selectors typical for overlay
    try:
        css_selectors = [
            "[data-role='inactivity-message-wrapper'] [data-role='play-button']",
            "[data-role='inactivity-message-clickable']",
            "button[data-role='play-button']",
            "[data-role='inactivity-message-wrapper'] button",
        ]
        for sel in css_selectors:
            try:
                el = WebDriverWait(driver, max(1, timeout_sec // 2)).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                # Try normal click, then JS click
                try:
                    WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    el.click()
                    _log(f"Clicked inactivity overlay via CSS selector: {sel}")
                    driver.switch_to.default_content()
                    return True
                except Exception:
                    driver.execute_script("arguments[0].click();", el)
                    _log(f"Clicked inactivity overlay via JS using CSS selector: {sel}")
                    driver.switch_to.default_content()
                    return True
            except TimeoutException:
                continue
    except Exception:
        pass

    # XPaths with likely texts
    xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'press to continue')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tap to continue')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'resume')]",
        "//div[@role='button' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
        "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
        "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'resume')]",
    ]

    try:
        for xp in xpaths:
            try:
                el = WebDriverWait(driver, max(1, timeout_sec // 2)).until(
                    EC.element_to_be_clickable((By.XPATH, xp))
                )
                el.click()
                _log(f"Clicked inactivity element via XPath: {xp}")
                driver.switch_to.default_content()
                return True
            except TimeoutException:
                continue
            except Exception:
                continue

        # If no button found, try a center click on the iframe area (often resumes)
        driver.switch_to.default_content()
        actions = ActionChains(driver)
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", iframe_el)
        except Exception:
            pass
        size = iframe_el.size
        offset_x = size.get("width", 0) / 2
        offset_y = size.get("height", 0) / 2
        actions.move_to_element_with_offset(iframe_el, offset_x, offset_y).click().perform()
        _log("Performed center click on evo iframe area (move_to_element_with_offset).")
        return True

    except Exception as e:
        _log(f"Error dismissing inactivity overlay: {e}")
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

    return False


def refresh_casino(
    debug_port: int = 9222,
    host_hint: Optional[str] = None,
    timeout_sec: int = 3,
    try_cdp_iframe_refresh: bool = True,
    fallback_full_reload: bool = True
) -> bool:
    """
    Attach to Chrome via remote debugging, focus the casino tab,
    check for session-expired and refresh if needed,
    refresh the evo iframe or dismiss inactivity, else refresh the full page.

    Returns True if any refresh/dismiss action was performed.
    """
    t0 = time.time()
    driver = None
    try:
        driver = _connect_driver(debug_port)
        _log(f"Attached to Chrome on 127.0.0.1:{debug_port}")

        # Focus target tab
        matched = _switch_to_target_tab(driver, host_hint)
        if not matched:
            _log("No matching tab for host hint or allowed hosts; proceeding with current tab.")

        # Top-level session-expired check
        if _refresh_if_expired(driver):
            _log("Page refreshed due to session expiry.")
            return True

        # Snapshot evo iframe and src
        evo_iframe = _find_evo_iframe_webelement(driver)
        evo_src_hint = None
        if evo_iframe:
            try:
                evo_src_hint = (evo_iframe.get_attribute("src") or "").lower()
            except Exception:
                evo_src_hint = None

        # Attempt CDP iframe-only refresh (fast)
        did_something = False
        if try_cdp_iframe_refresh:
            did_something = _refresh_iframe_via_cdp(driver, evo_src_hint)
            if did_something:
                time.sleep(0.5)

        # Try to dismiss inactivity overlay inside the iframe
        if not evo_iframe:
            evo_iframe = _find_evo_iframe_webelement(driver)
        if evo_iframe:
            try:
                time.sleep(0.25)
                if _try_dismiss_inactivity_buttons(driver, evo_iframe, timeout_sec=timeout_sec):
                    _log("Inactivity overlay dismissed successfully.")
                    return True
            except Exception:
                pass

        # If nothing worked, full page refresh
        if fallback_full_reload:
            _log("Falling back to full page reload...")
            driver.refresh()
            time.sleep(0.75)

            # Re-check session expired after refresh
            if _refresh_if_expired(driver):
                _log("Post-refresh: session expired handled.")
                return True

            evo_iframe = _find_evo_iframe_webelement(driver)
            if evo_iframe:
                try:
                    if _try_dismiss_inactivity_buttons(driver, evo_iframe, timeout_sec=timeout_sec):
                        _log("Inactivity overlay dismissed after full reload.")
                        return True
                except Exception:
                    pass

            return True  # At least did a full page reload

        return did_something

    except Exception as e:
        _log(f"Fatal error: {e}")
        return False
    finally:
        # Do not quit the driver; we're attached to an existing Chrome
        elapsed = time.time() - t0
        _log(f"Done in {elapsed:.2f}s.")


def refresh_once(
    debug_port: int = 9222,
    host_hint: Optional[str] = None,
    timeout_sec: int = 3
) -> bool:
    """Single-pass inactivity/session-expired bypass."""
    return refresh_casino(debug_port=debug_port, host_hint=host_hint, timeout_sec=timeout_sec)


def run_watchdog(
    debug_port: int = 9222,
    host_hint: Optional[str] = None,
    interval_sec: int = 3
) -> None:
    """
    Continuous loop: attempt bypass/refresh every interval_sec seconds until stopped.
    Safe to Ctrl+C to stop.
    """
    _log(f"Watchdog loop started: interval={interval_sec}s port={debug_port} host_hint={host_hint!r}")
    try:
        while True:
            try:
                refresh_casino(debug_port=debug_port, host_hint=host_hint, timeout_sec=3)
            except Exception as e:
                _log(f"Watchdog iteration error: {e}")
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        _log("Watchdog stopped by user.")


def _parse_args(argv: List[str]) -> Tuple[int, Optional[str]]:
    """
    Args:
        argv: [port?, host_hint?]
    Returns:
        (port, host_hint_regex or None)
    """
    port = 9222
    host_hint = None
    if len(argv) >= 2:
        try:
            port = int(argv[1])
        except ValueError:
            host_hint = argv[1]
    if len(argv) >= 3:
        host_hint = argv[2]
    return port, host_hint


if __name__ == "__main__":
    port, hint = _parse_args(sys.argv)

    # Detect loop/watch flag and optional interval (defaults to 3s)
    args_lower = [a.lower() for a in sys.argv[1:]]
    loop = any(a in ("--loop", "--watch", "loop", "watch") for a in args_lower)
    interval = 3
    # If a second int (besides port) is present, treat it as interval seconds
    ints = []
    for a in sys.argv[1:]:
        try:
            ints.append(int(a))
        except ValueError:
            pass
    if len(ints) >= 2:
        interval = ints[1]

    if loop:
        _log(f"Starting inactivity watchdog every {interval}s on port={port} host_hint={hint!r}")
        run_watchdog(debug_port=port, host_hint=hint, interval_sec=interval)
        sys.exit(0)
    else:
        _log(f"Starting inactivity bypass on port={port} host_hint={hint!r}")
        ok = refresh_casino(debug_port=port, host_hint=hint)
        sys.exit(0 if ok else 1)
