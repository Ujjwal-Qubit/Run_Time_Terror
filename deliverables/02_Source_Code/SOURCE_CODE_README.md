# SANKET — Source Code Distribution & Reproduction Guide
## Smart India Hackathon 2026 | Problem Statement 26169 (Department of Space / ISRO)

---

```
========================================================================================
                          SANKET SOURCE CODE REPRODUCTION GUIDE
========================================================================================
  System Name:         SANKET (AI-Assisted FSOC Virtual Camera Tracking System)
  Organization:        Department of Space / Indian Space Research Organisation (ISRO)
  Deliverable Number:  Deliverable 02 — Source Code
  Archive File:        SANKET_Source.zip (30.36 MB clean source archive)
  Backend Stack:       Python 3.11.9 / OpenCV 4.10 / NumPy / PySide6 (QtWebEngine)
  Frontend Stack:      React 19 / TypeScript / Vite / TailwindCSS / Three.js
  Automated Tests:     599 / 599 Pytest Units & Integration Suites Passing
========================================================================================
```

---

## 1. Repository Architecture & Layout

```text
SANKET/
+-- src/                                # Complete Python backend and algorithm stack
|   +-- aiml/                           # AI/ML candidate classifier, feature extractor, temporal predictor
|   +-- api/                            # High-level API contracts and interfaces
|   +-- app/                            # Application controller and PySide6/WebEngine GUI host
|   |   +-- app_controller.py           # Main system lifecycle coordinator and frame pipeline
|   |   \-- gui/                        # QtWebEngine / QtWebChannel host window and bridge
|   +-- config/                         # Configuration schema, dataclasses, and JSON persistence
|   +-- control/                        # PTZ closed-loop PID controller with rate limits and deadband
|   +-- data/                           # Dataset handling and generation scripts
|   +-- evaluation/                     # BenchmarkManager, automated matrix runner, AI scenario engine
|   +-- frame/                          # Frame providers: SimulationFrameProvider and MP4FrameProvider
|   +-- interfaces/                     # Strategy interfaces (IDetectionEngine, IPTZController, etc.)
|   +-- metrics/                        # Real-time metrics engine, logging engine, SIH compliance evaluator
|   +-- plugins/                        # Dynamic plugin loader and algorithm implementations
|   +-- simulation/                     # Virtual scene generator, target manager, camera FPA, disturbances
|   +-- tests/                          # Pytest test suite (599 automated unit and integration tests)
|   +-- tracker/                        # Detection engine, candidate identifier, sub-pixel centroid, state machine
|   \-- main.py                         # Primary system entry point (CLI and GUI dispatcher)
+-- frontend/                           # Embedded React / TypeScript / Tailwind / Three.js GUI
|   +-- src/
|   |   +-- components/                 # Reusable UI widgets (Header, Footer, Navigation, Ribbon)
|   |   +-- workspaces/                 # 5 production workspaces
|   |   |   +-- DeveloperWorkspace/     # 2D Sensor View, 3D Pedestal Frustum, 2000x2000 World Canvas
|   |   |   +-- EvaluatorWorkspace/     # Benchmark-1 & Benchmark-2 evaluation console
|   |   |   +-- DiagnosticsWorkspace/   # Subsystem audit and airgap compliance monitor
|   |   |   +-- HistoryWorkspace/       # Run history and artifact catalog browser
|   |   |   \-- ResultsWorkspace/       # Detailed statistical charts and scorecard inspector
|   |   +-- services/                   # QtWebChannel transport bridge and IPC connector
|   |   +-- store/                      # Zustand state management store
|   |   \-- types/                      # TypeScript interface definitions for telemetry and configuration
|   +-- package.json                    # Frontend package configuration and dependencies
|   +-- tailwind.config.js              # Industrial theme color tokens and design system
|   \-- vite.config.ts                  # Vite production bundler configuration
+-- App_Logo_Assets_Final/              # Official SANKET vector and raster branding assets
+-- scenarios/                          # JSON scenario definitions (19 matrix vectors + baselines)
+-- scripts/                            # Automated audit, screenshot capture, packaging, and validation tools
+-- installer/                          # Inno Setup 6 packaging configuration (`sanket_setup.iss`)
+-- models/                             # Trained machine learning model weights (`candidate_classifier.json`)
+-- docs/                               # Official documentation, specifications, and figures
+-- deliverables/                       # Standardized submission folder structure
+-- lr_model.json                       # Calibrated logistic regression candidate classifier weights
+-- sanket.spec                         # PyInstaller specification for standalone ONEDIR binary
+-- requirements.txt                    # Python backend dependencies
+-- pytest.ini                          # Pytest runner configuration
\-- run_sanket.bat                      # Windows launcher script
```

---

## 2. Build Requirements & Prerequisites

To reproduce the build from source on a Windows host:

### 2.1 Software Prerequisites
1. **Operating System:** Windows 10 or Windows 11 (64-bit).
2. **Python Runtime:** Python 3.11.x (tested on 3.11.9 64-bit). Ensure Python and `pip` are added to your system `PATH`.
3. **Node.js Environment:** Node.js 18.x or 20.x LTS with `npm`.
4. **C++ Runtimes:** Microsoft Visual C++ 2015–2022 Redistributable (x64).
5. **Inno Setup (Optional):** Inno Setup 6.2+ if compiling the Windows installer (`SANKET-Setup-v1.0.exe`).

---

## 3. Step-by-Step Reproduction Instructions

### Step 1: Clone or Extract Repository
```powershell
# If using git:
git clone https://github.com/Ujjwal-Qubit/Run_Time_Error.git SANKET
cd SANKET

# If using SANKET_Source.zip:
Expand-Archive -Path SANKET_Source.zip -DestinationPath .\SANKET
cd SANKET
```

### Step 2: Set Up Python Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verified core dependencies in `requirements.txt`:
- `PySide6 >= 6.7.0` (GUI host & embedded Chromium QWebEngine)
- `opencv-python >= 4.10.0` (Computer vision algorithms & MP4 decoding)
- `numpy >= 1.26.0` (High-performance array operations)
- `scipy >= 1.13.0` (Scientific filters and spatial operations)
- `reportlab >= 4.2.0` (Automated PDF document generation)
- `pypdf >= 4.2.0` (PDF inspection and page verification)
- `pytest >= 8.2.0` (Automated test execution)

### Step 3: Compile Frontend Assets
```powershell
cd frontend
npm install
npm run build
cd ..
```
The compiled React production bundle is written into `frontend/dist/`. This single-page application is automatically served locally to QtWebEngine by the Python runtime via QWebChannel IPC.

### Step 4: Run Automated Tests
```powershell
pytest
```
Verify that all 599 tests pass with zero failures.

### Step 5: Launch SANKET from Source
```powershell
# Launch the full graphical workstation:
python -m src.main

# Or execute headlessly:
python -m src.main --headless --scenario scenario_2_circular --duration 30
```

---

## 4. Standalone Executable Packaging (PyInstaller)

To compile the standalone distribution (`deliverables/01_Software_Application/SANKET/SANKET.exe`):

```powershell
pyinstaller sanket.spec --noconfirm --clean
```

The output bundle is generated at:
```text
dist/SANKET/
├── SANKET.exe
├── _internal/
├── scenarios/
├── models/
├── Videos/
└── lr_model.json
```

---

## 5. Verification Commands

| Command | Purpose | Expected Output |
| :--- | :--- | :--- |
| `python -m src.main --validate` | Internal contract & subsystem health check | 8/8 Subsystems Passed |
| `pytest` | Complete unit and integration test suite | 599 passed in ~120s |
| `python scripts/capture_all_documentation_screenshots.py` | Live UI screenshot capture suite | All 18 screenshots captured |
| `python scripts/generate_sanket_technical_report_pdf.py` | Compile 15-page Technical Report PDF | PDF built successfully |
| `python scripts/generate_sanket_user_manual_pdf.py` | Compile 10-page User Manual PDF | PDF built successfully |
| `python scripts/generate_sanket_performance_pdf.py` | Compile Performance Verification PDF | PDF built successfully |
| `python scripts/generate_sanket_manifest_pdf.py` | Compile Deliverables Manifest PDF | PDF built successfully |
