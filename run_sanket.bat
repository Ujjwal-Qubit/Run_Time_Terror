@echo off
pushd "%~dp0"
REM ============================================================================
REM SANKET — AI-Assisted FSOC Virtual Camera Tracking System Launcher
REM SIH 2026 Problem Statement PS-26169 (Department of Space / ISRO)
REM Prefers compiled standalone binary if present; falls back to python module.
REM ============================================================================

SET "EXE_PATH=%~dp0deliverables\01_Software_Application\SANKET\SANKET.exe"
IF NOT EXIST "%EXE_PATH%" (
    SET "EXE_PATH=%~dp0dist\SANKET\SANKET.exe"
)

IF EXIST "%EXE_PATH%" (
    echo [SANKET] Starting standalone executable:
    echo          "%EXE_PATH%"
    IF "%~1"=="" (
        "%EXE_PATH%" --gui
    ) ELSE (
        "%EXE_PATH%" %*
    )
) ELSE (
    echo [SANKET] Standalone executable not found in deliverables\ or dist\.
    echo [SANKET] Falling back to local Python module execution...
    IF "%~1"=="" (
        python -m src.main --gui
    ) ELSE (
        python -m src.main %*
    )
)

SET "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
