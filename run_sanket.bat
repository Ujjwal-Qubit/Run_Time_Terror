@echo off
pushd "%~dp0"
REM SANKET — AI-Assisted FSOC Virtual Camera Tracking System Launcher
REM Prefers compiled standalone binary if present; falls back to python module.

SET EXE_PATH=%~dp0dist\SANKET\SANKET.exe

IF EXIST "%EXE_PATH%" (
    IF "%~1"=="" (
        "%EXE_PATH%" --gui
    ) ELSE (
        "%EXE_PATH%" %*
    )
) ELSE (
    IF "%~1"=="" (
        python -m src.main --gui
    ) ELSE (
        python -m src.main %*
    )
)
popd
