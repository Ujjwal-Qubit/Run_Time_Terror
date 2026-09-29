========================================================================
SANKET - Free Space Optical Communication (FSOC) Tracking System
Standalone Software Application Package (Deliverable 01)
SIH 2026 Problem Statement PS-26169
Department of Space / Indian Space Research Organisation (ISRO)
========================================================================

PACKAGE CONTENTS:
1. SANKET/
   - The complete standalone ONEDIR distribution.
   - Primary executable: SANKET/SANKET.exe
   - Embedded runtime: SANKET/_internal/ (contains bundled Python 3.11 runtime,
     PySide6, QtWebEngine, OpenCV, bundled React production build, scenarios,
     logo assets, and model weights).
   - Zero external installation required: completely self-contained and air-gap compliant.

2. installer/
   - SANKET-Setup-v1.0.exe: Standard Windows Inno Setup 6 installer that installs
     SANKET to %LOCALAPPDATA%\Programs\SANKET and creates optional Start Menu
     and Desktop shortcuts with official logo branding.

3. portable/
   - SANKET-Portable-v1.0.zip: Standalone portable archive. Extract anywhere and run.

HOW TO RUN:
Option A (Direct Execution from folder):
  Navigate to "SANKET\" and double-click "SANKET.exe", or run from terminal:
    cd SANKET
    .\SANKET.exe

Option B (Installer):
  Navigate to "installer\" and run "SANKET-Setup-v1.0.exe". Follow on-screen prompts.

Option C (Command Line Modes):
  .\SANKET.exe                       # Default: Launches interactive 5-workspace GUI
  .\SANKET.exe --headless            # Runs simulation loop headlessly in console
  .\SANKET.exe --scenario <name>     # Loads a named scenario (e.g. scenario_2_circular)
  .\SANKET.exe --validate            # Executes internal foundation validation audit
  .\SANKET.exe --matrix SMOKE        # Executes automated test matrix suite
  .\SANKET.exe --mp4 <path>          # Benchmark-2 external video ingestion mode

SYSTEM REQUIREMENTS:
- Operating System: Windows 10 / 11 (64-bit)
- Hardware: x86_64 CPU (Dual-core or higher), min 4 GB RAM, 1 GB free disk space
- GPU: DirectX 11 / OpenGL 3.3 compatible (hardware acceleration utilized by QtWebEngine)
- Clean-machine immunity: MSVC runtimes (msvcp140.dll, etc.) are bundled directly.
========================================================================
