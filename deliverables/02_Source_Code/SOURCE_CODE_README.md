# SANKET — Source Code Distribution & Reproduction Guide

**Problem Statement:** SIH 2026 Problem Statement 26169  
**System Name:** SANKET — AI-Assisted Free-Space Optical Communication (FSOC) Tracking System  
**Organization:** Department of Space / Indian Space Research Organisation (ISRO)  
**Deliverable:** 02_Source_Code  
**Archive:** `SANKET_Source.zip` (26.53 MB, 281 clean source files)

---

## 1. Project Directory Structure

```
SANKET/
├── src/                            # Complete Python backend and algorithm stack
│   ├── aiml/                       # AI/ML candidate classifier, feature extractor, temporal predictor
│   ├── api/                        # High-level API contracts and interfaces
│   ├── app/                        # Application controller and PySide6/WebEngine GUI host
│   │   ├── app_controller.py       # Main system lifecycle coordinator and frame pipeline
│   │   └── gui/                    # QtWebEngine / QtWebChannel host window and bridge
│   ├── config/                     # Configuration schema, dataclasses, and JSON persistence
│   ├── control/                    # PTZ closed-loop PID controller with rate limits and deadband
│   ├── data/                       # Dataset handling and generation scripts
│   ├── evaluation/                 # BenchmarkManager, automated matrix runner, AI scenario engine
│   ├── frame/                      # Frame providers: SimulationFrameProvider and MP4FrameProvider
│   ├── interfaces/                 # Strict Strategy interfaces (IDetectionEngine, IPTZController, etc.)
│   ├── metrics/                    # Real-time metrics engine, logging engine, SIH compliance evaluator
│   ├── plugins/                    # Dynamic plugin loader and algorithm implementations
│   ├── simulation/                 # Virtual scene generator, target manager, camera FPA, disturbances
│   ├── tests/                      # Pytest test suite (492 automated unit and integration tests)
│   ├── tracker/                    # Detection engine, candidate identifier, sub-pixel centroid, state machine
│   └── main.py                     # Primary system entry point (CLI and GUI dispatcher)
├── frontend/                       # Embedded React / TypeScript / Tailwind / Three.js GUI
│   ├── src/
│   │   ├── components/             # Reusable UI widgets (Header, Footer, Navigation, Ribbon)
│   │   ├── workspaces/             # 5 production workspaces
│   │   │   ├── DeveloperWorkspace/ # 2D Sensor View, 3D Pedestal Frustum, 2000x2000 World Canvas
│   │   │   ├── EvaluatorWorkspace/ # Benchmark-1 & Benchmark-2 evaluation console
│   │   │   ├── DiagnosticsWorkspace/# Subsystem audit and airgap compliance monitor
│   │   │   ├── HistoryWorkspace/   # Run history and artifact catalog browser
│   │   │   └── ResultsWorkspace/   # Detailed statistical charts and scorecard inspector
│   │   ├── services/               # QtWebChannel transport bridge and IPC connector
│   │   ├── store/                  # Zustand state management store
│   │   └── types/                  # TypeScript interface definitions for telemetry and configuration
│   ├── package.json                # Frontend package configuration and dependencies
│   ├── tailwind.config.js          # Industrial theme color tokens and design system
│   └── vite.config.ts              # Vite production bundler configuration
├── App_Logo_Assets_Final/          # Official SANKET vector and raster branding assets
├── scenarios/                      # JSON scenario definitions (static, circular, figure8, fog)
├── scripts/                        # Automated audit, screenshot capture, packaging, and validation tools
├── installer/                      # Inno Setup 6 packaging configuration (`sanket_setup.iss`)
├── models/                         # Trained machine learning model weights (`candidate_classifier.json`)
├── docs/                           # Official problem statement, PRD, and architecture specifications
├── lr_model.json                   # Calibrated logistic regression candidate classifier weights
├── sanket.spec                     # PyInstaller specification for standalone ONEDIR binary
├── requirements.txt                # Python backend dependencies
├── pytest.ini                      # Pytest runner configuration
└── run_sanket.bat                  # Windows launcher script
```

---

## 2. Environment Setup & Prerequisites

### System Requirements
- **Operating System:** Windows 10 / 11 (64-bit) (or Linux with QtWebEngine support)
- **Python:** Python 3.10, 3.11, or 3.12 (64-bit)
- **Node.js:** Node.js v18.0.0 or higher with `npm`

### Step 1: Create and Activate Python Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Backend Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

*Contents of `requirements.txt`:*
```
numpy>=1.24.0
opencv-python>=4.8.0
PySide6>=6.5.0
pytest>=8.0.0
```

---

## 3. Frontend Build Instructions

The frontend is built using Vite and TypeScript into static assets served via local QtWebEngine:

```powershell
cd frontend
npm install
npm run build
cd ..
```

This generates `frontend/dist/index.html` and bundled assets in `frontend/dist/assets/`.

---

## 4. Running the Application

### Launch Modern 5-Workspace GUI (Default)
```powershell
python -m src.main
```
or simply execute the convenience script:
```cmd
run_sanket.bat
```

### Run Simulation Headlessly (Console Mode)
```powershell
# Run default simulation headlessly
python -m src.main --headless

# Run specific scenario
python -m src.main --headless --scenario scenario_2_circular
```

### Run Benchmark Matrix
```powershell
python -m src.main --matrix SMOKE
python -m src.main --matrix ALL
```

### Run Benchmark-2 External Video Ingestion
```powershell
python -m src.main --mp4 "path/to/video.mp4" --reference-csv "path/to/ground_truth.csv"
```

### Validate Foundation & Interface Contracts
```powershell
python -m src.main --validate
```

---

## 5. Running the Automated Test Suite

SANKET includes a comprehensive test suite covering all modules:

```powershell
python -m pytest
```

*Verified test results (Python 3.11.9):*
```
============================ 492 passed in 19.39s =============================
```

To run specific test modules:
```powershell
# Benchmark-2 workflow tests
pytest src/tests/test_bm2_workflow.py

# PTZ controller tests
pytest src/tests/test_ptz_controller.py

# AI candidate classifier tests
pytest src/tests/test_ai_classifier.py
```

---

## 6. Building the Standalone Executable (PyInstaller)

To build the standalone Windows executable identical to `deliverables/01_Software_Application/`:

1. Ensure the frontend is built (`npm run build` in `frontend/`).
2. Run PyInstaller using the project specification:
```powershell
pyinstaller sanket.spec --noconfirm --clean
```
3. The packaged executable is placed in `dist/SANKET/SANKET.exe`.

To build the Windows installer (requires Inno Setup 6):
```cmd
"C:\Users\<user>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\sanket_setup.iss
```
This generates `dist/SANKET-Setup-v1.0.exe`.

---

## 7. Entry Points Summary

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Backend CLI / Dispatcher** | `src/main.py` | Argument parsing, mode selection, GUI/headless launcher |
| **Backend Core Controller** | `src/app/app_controller.py` | Orchestrates simulation, tracking, control, logging |
| **GUI PySide6 Host** | `src/app/gui/web_window.py` | PySide6 QWebEngineView window hosting the React UI with official SANKET icon |
| **Frontend Entry Point** | `frontend/src/main.tsx` | React 19 root mounting `App.tsx` |
| **Frontend Application** | `frontend/src/App.tsx` | Workspace tab routing, theme management, bridge lifecycle |
| **IPC Bridge** | `frontend/src/services/qtBridge.ts` | QtWebChannel WebSocket/memory bridge transport |
| **Algorithm Strategy API** | `src/interfaces/strategy_interfaces.py` | Abstract interfaces for detection, tracking, PTZ |
