# Deliverable 06: Demonstration Video (Optional)

**Problem Statement:** SIH 2026 Problem Statement 26169  
**Deliverable:** 06_Optional_Demo_Video  
**Status:** NOT AVAILABLE IN BUILD ENVIRONMENT (READY FOR LIVE PRESENTATION / EXTERNAL CAPTURE)  

---

## Status & Clarification

Under SIH Problem Statement 26169, Deliverable 6 (3–5 minute demonstration video) is designated as **OPTIONAL** ("A 3–5 minutes video may also be provided as an optional deliverable for demonstration of the application").

In the automated build, test, and packaging environment, physical microphone audio capture and GPU desktop video recording software (e.g. OBS Studio, Windows Game Bar) are not present. To adhere strictly to the **NO FABRICATION RULE** and deliverable truthfulness:
- No synthetic or mock video file has been fabricated.
- The live executable application is provided in **Deliverable 01 (`deliverables/01_Software_Application/`)** and verified ready for live evaluation.

---

## Recommended Live Demonstration Flow (3–5 Minutes)

For evaluators conducting live functional verification:

1. **Launch SANKET (0:00 - 0:30):**
   - Run `SANKET.exe`. The 5-workspace workstation opens immediately with official branding.
   - Point out the air-gap compliance indicator and offline status in the footer.

2. **Developer Workspace — 2D Sensor View (0:30 - 1:30):**
   - Click **RUN** to initiate circular beacon tracking.
   - Observe real-time sub-pixel centroiding (green crosshair), bounding box, and boresight vector.
   - Adjust disturbance sliders in real time: inject **Gaussian Noise ($\sigma = 15$)**, **Salt & Pepper (8%)**, and **Atmospheric Fog**.
   - Observe tracking continuity and closed-loop PTZ centering.

3. **Developer Workspace — 3D Pedestal Frustum (1:30 - 2:30):**
   - Switch to the **3D Pedestal Frustum** sub-view.
   - Observe real-time 3D camera gimbal articulation (pan/tilt) and optical beam cone intersecting the target plane.

4. **Developer Workspace — 2000×2000 World Canvas (2:30 - 3:15):**
   - Switch to the **World Canvas** sub-view.
   - Observe the 2000×2000 global terrain coordinate system, target orbit, and moving 640×480 camera FOV footprint.
   - Note the **LIVE OPERATIONAL: WORLD GT STRIPPED** indicator verifying the architectural firewall.

5. **Evaluator & Diagnostics Workspaces (3:15 - 4:00):**
   - Navigate to **Evaluator Workspace** to show Benchmark-1 and Benchmark-2 execution consoles.
   - Navigate to **Diagnostics & Subsystem Audit** to verify 492 passing unit tests and system health telemetry.
   - Navigate to **Results & Analysis** to inspect automatically generated performance logs, latency percentiles, and SIH compliance scorecards.
