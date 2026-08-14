@echo off
title Local AI Coding Agent - Web UI Server
cls
echo ===================================================
echo     Starting Local AI Coding Agent Web UI
echo     Opening http://127.0.0.1:5050 in browser
echo ===================================================
start "" http://127.0.0.1:5050
python main.py web --port 5050
pause
