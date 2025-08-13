@echo off
setlocal

set "URL_TO_OPEN=https://casino.draftkings.com"
if not "%~1"=="" set "URL_TO_OPEN=%~1"

echo Stopping all existing Chrome processes...
taskkill /f /im chrome.exe 2>nul
taskkill /f /im "Google Chrome.exe" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting Chrome with proper debugging flags...
echo Target URL: %URL_TO_OPEN%
echo.

set "CHROME_PATH_1=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHROME_PATH_2=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set "CHROME_PATH_3=%USERPROFILE%\AppData\Local\Google\Chrome\Application\chrome.exe"

echo Checking path 1: %CHROME_PATH_1%
if exist "%CHROME_PATH_1%" (
    echo Found Chrome. Launching...
    start "" "%CHROME_PATH_1%" --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug" "%URL_TO_OPEN%"
    goto :end
)

echo Checking path 2: %CHROME_PATH_2%
if exist "%CHROME_PATH_2%" (
    echo Found Chrome. Launching...
    start "" "%CHROME_PATH_2%" --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug" "%URL_TO_OPEN%"
    goto :end
)

echo Checking path 3: %CHROME_PATH_3%
if exist "%CHROME_PATH_3%" (
    echo Found Chrome. Launching...
    start "" "%CHROME_PATH_3%" --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug" "%URL_TO_OPEN%"
    goto :end
)

echo.
echo ❌ ERROR: Could not find a Chrome installation in any standard location!
echo Please manually start Chrome with these exact flags, replacing the URL if needed:
echo.
echo chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --disable-web-security --user-data-dir="%TEMP%\chrome_debug" "%URL_TO_OPEN%"
echo.

:end
echo.
echo ✅ Chrome launch command sent.
echo.
endlocal
