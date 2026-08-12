@echo off
title Steam Classifier
echo Starting Steam Classifier...
echo A browser tab will open at http://127.0.0.1:5000
echo Close this window to stop the app.
python -m pip install -r requirements.txt >nul 2>&1
python app.py
pause
