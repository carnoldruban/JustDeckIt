@echo off
echo Killing Chrome instances with remote debugging port 9222...
for /f "tokens=5" %%i in ('netstat -ano ^| findstr :9222') do taskkill /F /PID %%i > nul 2>&1

echo.
echo Launching Chrome with remote debugging on port 9222...
start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 "https://casino.draftkings.com"

echo.
echo Chrome has been launched. Please log in and navigate to the game page, then click "Start Tracking" in the app.
