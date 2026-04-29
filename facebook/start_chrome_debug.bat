@echo off
rem Start Chrome with remote debugging on port 9222
rem This opens a new Chrome window (separate from your existing Chrome)
rem that can be controlled by the scraper.

start "" "C:\soft\chrome\chrome-win64\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_profile"
echo Chrome started with debugging on port 9222
pause
