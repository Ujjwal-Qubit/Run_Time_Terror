@echo off
pushd "%~dp0"
REM LumiTrack — Modern Web Interface Launcher
echo ==========================================================
echo Starting LumiTrack Web Platform (FastAPI + Vite/React)
echo Open http://127.0.0.1:8000 in your browser
echo ==========================================================

REM Check if frontend node_modules exists
IF NOT EXIST "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    call npm --prefix frontend install
)

REM Check if frontend production build exists
IF NOT EXIST "frontend\dist\index.html" (
    echo [INFO] Building frontend distribution...
    call npm --prefix frontend run build
)

IF EXIST ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m src.main --web --port 8000
) ELSE (
    python -m src.main --web --port 8000
)
popd
