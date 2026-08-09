@echo off
title Steam Collection Auto-Tagger

echo.
echo ============================================================
echo   Steam Collection Auto-Tagger
echo ============================================================
echo.
echo Before you start:
echo   1. Close Steam completely
echo   2. Get a free API key from: https://steamcommunity.com/dev/apikey
echo      (Use any domain name, e.g. localhost)
echo   3. Find your 64-bit Steam ID at: https://www.steamidfinder.com/
echo      (It's a 17-digit number starting with 76561)
echo.
echo ============================================================
echo.

set /p API_KEY="Paste your Steam API key: "
if "%API_KEY%"=="" (
    echo No API key entered. Exiting.
    pause
    exit /b 1
)

set /p STEAM_ID="Paste your 64-bit Steam ID: "
if "%STEAM_ID%"=="" (
    echo No Steam ID entered. Exiting.
    pause
    exit /b 1
)

echo.
echo Running preview (no changes will be made)...
echo Note: new/unrecognized games won't be asked about yet during preview.
echo ============================================================
echo.

python steam_categorizer_v2.py --api-key %API_KEY% --steam-id %STEAM_ID% --dry-run --overwrite

echo.
echo ============================================================
echo.
set /p CONFIRM="Look good? Type YES to apply changes, anything else to cancel: "

if /i "%CONFIRM%"=="YES" (
    echo.
    echo Applying categories...
    echo If any new games are found, you'll be asked to confirm a category
    echo for each one right here - just follow the prompts.
    echo.
    python steam_categorizer_v2.py --api-key %API_KEY% --steam-id %STEAM_ID% --overwrite
    echo.
    echo Done! You can now open Steam.
) else (
    echo.
    echo Cancelled. No changes were made.
)

echo.
pause
