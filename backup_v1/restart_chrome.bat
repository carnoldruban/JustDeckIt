@echo off
echo Killing any existing Chrome processes...
taskkill /F /IM chrome.exe /T > nul

echo.
echo Launching Chrome with remote debugging on port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 "https://casino.draftkings.com"

echo.
echo Chrome has been launched. Please log in and navigate to the game page, then click "Start Tracking" in the app.
