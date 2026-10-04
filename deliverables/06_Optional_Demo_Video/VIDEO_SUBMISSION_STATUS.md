# Deliverable 06: Demonstration Video (Optional)

**Problem Statement:** SIH 2026 Problem Statement 26169 (Department of Space / ISRO)  
**System Name:** SANKET — AI-Assisted Free-Space Optical Communication (FSOC) Tracking System  
**Deliverable Number:** Deliverable 06 — Demonstration Video (Optional)  
**Video File:** `SANKET_Launch_Demo.mp4`  
**Status:** COMPLETE & PACKAGED IN SUBMISSION DIRECTORY  

---

## 1. Video Specifications & Metadata

| Property | Value |
| :--- | :--- |
| **File Name** | `SANKET_Launch_Demo.mp4` |
| **File Location** | `deliverables/06_Optional_Demo_Video/SANKET_Launch_Demo.mp4` |
| **Secondary Location** | `docs/assets/SANKET_Launch_Demo.mp4` |
| **Video Resolution** | **1920 × 1080 (Full HD 1080p)** |
| **Frame Rate** | **30.0 FPS** |
| **Frame Count** | 660 Frames |
| **Duration** | **22.0 Seconds** |
| **Video Codec** | H.264 (AVC) Baseline Profile |
| **File Size** | **4,602,005 Bytes (4.60 MB)** |
| **Visual Preview** | `docs/assets/demo_preview.gif` (10.2 MB animated GIF) |
| **Poster Frame** | `docs/assets/demo_poster.png` (694.8 KB PNG) |

---

## 2. Video Content & Workflow Sequence

The demonstration video highlights the core operational capabilities of SANKET:

1. **System Introduction & Launch:** Official SANKET branding, air-gapped SIL architecture verification, and workspace initialization.
2. **Developer Workspace — 2D Sensor Tracking:** Live 640×480 monochrome FPA detector feed, sub-pixel centroiding reticle, optical boresight crosshair alignment, and real-time bounding box tracking.
3. **Developer Workspace — 3D Pedestal Frustum:** Interactive Three.js 3D gimbal model showing real-time pan/tilt mechanical articulation and optical beam cone projection.
4. **Developer Workspace — 2000×2000 World Canvas:** Wide-area spatial monitoring illustrating beacon orbital transit and moving camera sensor footprint with ground-truth firewall verification.
5. **Evaluator Console & Benchmark Execution:** Overview of Benchmark-1 (19-Scenario Matrix) and Benchmark-2 (External Video Evaluator in PTZ Bypass Mode).

---

## 3. Alternative Verification Options for Evaluators

In addition to viewing the bundled MP4 video file, evaluators can experience the live interactive software directly:

- **Launch Interactive GUI:**
  ```powershell
  .\SANKET.exe
  ```
- **Run Automated Headless Simulation:**
  ```powershell
  .\SANKET.exe --headless --scenario scenario_2_circular --duration 30
  ```
- **Execute Automated Benchmark Matrix:**
  ```powershell
  .\SANKET.exe --matrix SMOKE
  ```
