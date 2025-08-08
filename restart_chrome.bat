@echo off
echo Stopping all existing Chrome processes...
taskkill /f /im chrome.exe 2>nul
taskkill /f /im "Google Chrome.exe" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting Chrome with proper debugging flags...
echo.

REM Try standard Program Files location
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    echo Found Chrome in Program Files. Launching...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug" "https://casino.draftkings.com"
    goto :end
)

REM Try Program Files (x86) location
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    echo Found Chrome in Program Files (x86). Launching...
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug" "https://casino.draftkings.com"
    goto :end
)

REM Try user profile location
if exist "%USERPROFILE%\AppData\Local\Google\Chrome\Application\chrome.exe" (
    echo Found Chrome in user profile. Launching...
    start "" "%USERPROFILE%\AppData\Local\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug" "https://casino.draftkings.com"
    goto :end
)

echo.
echo ❌ ERROR: Could not find a Chrome installation in standard locations!
echo Please manually start Chrome with these exact flags:
echo.
echo chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug"
echo.

:end
echo.
echo ✅ Chrome launch command sent. Please navigate to the blackjack game.
echo You can now run the Python capture script.
echo.
