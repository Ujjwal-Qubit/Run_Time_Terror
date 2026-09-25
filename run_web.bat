@echo off
REM LumiTrack — Modern Web Interface Launcher
echo ==========================================================
echo Starting LumiTrack Web Platform (FastAPI + Vite/React)
echo Open http://127.0.0.1:8000 in your browser
echo ==========================================================

IF EXIST ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m src.main --web --port 8000
) ELSE (
    python -m src.main --web --port 8000
)
