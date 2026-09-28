# SIH 26169 — Security, Reliability, and Threat Modeling Audit

**Document ID**: `AUDIT-09-SECURITY-RELIABILITY`  
**Target Repository**: `Ujjwal-Qubit/Run_Time_Error` (SIH 26169 Coarse Alignment FSOC)  
**Status**: COMPLETE / FORENSIC VERIFIED  
**Auditor**: Antigravity First-Principles Reconnaissance

---

## 1. Threat Modeling for an FSOC Coarse Tracking Terminal

In a real-world military, aerospace, or critical infrastructure Free Space Optical Communication (FSOC) deployment (e.g. satellite-to-ground, UAV-to-ground, or mobile tactical convoy), the tracking terminal operates in an adversarial or hostile physical and cyber environment.

We evaluate the system against the STRIDE threat model:

| STRIDE Category | Physical / Cyber Attack Vector in FSOC | Current Codebase Status | Vulnerability Rating |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Optical decoy beacon / Laser dazzler / False beacon flashing at beacon wavelength | Tracker picks highest intensity contour; no temporal beacon modulation or crypto handshake. | **CRITICAL** |
| **Tampering** | Injected telemetry over unauthenticated WebSocket or REST API | All REST endpoints and WebSockets accept unauthenticated, unencrypted JSON payloads. | **HIGH** |
| **Repudiation** | Unaudited manual override or gimbal commands | Audit logging is purely ephemeral stdout/logging; no immutable audit log. | **MEDIUM** |
| **Information Disclosure** | Leakage of terminal GPS / gimbal pointing angles via open broadcast | `/ws/telemetry` broadcasts precise azimuth, elevation, and target coordinates to `0.0.0.0:*`. | **HIGH** |
| **Denial of Service (DoS)** | Optical blinding (saturation) OR network flood of WebSocket port | Sensor saturation blinds tracker completely; API has zero rate limiting and runs on main event loop. | **CRITICAL** |
| **Elevation of Privilege** | Remote arbitrary configuration injection via `/api/config` | Clients can overwrite arbitrary internal parameters (e.g. `gimbal_speed`, `roi_size`) without authorization. | **HIGH** |

---

## 2. API & Network Attack Surface Analysis (`src/api/server.py`)

The inclusion of a FastAPI/Uvicorn HTTP & WebSocket server (`src/api/server.py`) introduces a severe, completely unmitigated network attack surface into what should be an isolated real-time tracking controller.

### 2.1 Wildcard CORS (`allow_origins=["*"]`)
```python
# src/api/server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- **Risk**: Any malicious website visited by an operator on the same local subnet or terminal workstation can execute Cross-Origin Resource Sharing (CORS) attacks, making unauthenticated REST calls to start/stop the tracker, move the gimbal, or inject arbitrary disturbance profiles.

### 2.2 Unauthenticated WebSocket Endpoints
- The endpoint `/ws/stream` and `/ws/control` have **zero authentication tokens, mutual TLS, or API keys**:
  ```python
  @app.websocket("/ws/control")
  async def websocket_control(websocket: WebSocket):
      await websocket.accept()
      while True:
          data = await websocket.receive_json()
          # Executes control commands directly!
          controller.handle_remote_command(data)
  ```
- **Vulnerability**: Any client on the local network can connect and issue arbitrary pan/tilt commands or inject simulated targets.

### 2.3 Denial of Service via Unbounded Payloads & Blocking Calls
- FastAPI endpoints accept JSON payloads without maximum size limits (`max_body_size`).
- Large JSON strings or Malformed payloads can crash the Uvicorn worker.
- Since synchronous image processing runs on the same loop as WebSocket broadcasting, an attacker flooding the `/api/scenario` endpoint with complex requests will freeze the video stream and stall gimbal control.

---

## 3. Physical & Optical Reliability Defenses

### 3.1 Resistance to Optical Dazzling & Sensor Blinding
- In `src/tracker/baseline_tracker.py`:
  - Target detection relies on `cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY)`.
  - If an adversary shines a continuous-wave (CW) dazzler or high-power searchlight into the aperture:
    1. The entire sensor saturates (pixel values $\to 255$).
    2. `cv2.findContours` produces a single massive contour encompassing the entire image ($640 \times 480$).
    3. The tracker classifies this as an oversized contour, filters it out, and sets state to `LOST`.
    4. **Result**: The gimbal halts completely and never recovers, resulting in permanent communication link loss.
- **Missing Defense**: Automatic exposure control (AEC), digital neutral density / shutter throttling, adaptive local histogram equalization (CLAHE), and spatial bandpass filtering.

### 3.2 Sunlight & Cloud Edge Glint Resilience
- Clouds and solar reflections in real atmospheric FSOC produce specular glints with intensities exceeding $10^5 \text{ W/m}^2$.
- The current 4-feature classifier in `src/tracker/ai_classifier.py` checks:
  1. `area`
  2. `aspect_ratio`
  3. `circularity`
  4. `mean_intensity`
- A distant cloud glint has circularity $\approx 0.8$ and high intensity. The classifier cannot distinguish a solar glint from an FSOC laser beacon without spectral filtering, polarization filtering, or pulsed temporal beacon modulation.

---

## 4. Control Law Reliability & Fail-Safes

### 4.1 Gimbal Runaway & Anti-Windup Deficiencies
- In `src/control/ptz_controller.py`:
  - The controller uses an accumulator for integral error:
    ```python
    self.integral_pan += err_x * dt
    self.integral_tilt += err_y * dt
    ```
  - While output velocities are clamped to `max_velocity`, the integral accumulators (`integral_pan`, `integral_tilt`) are **not clamped** during saturation (integrator windup).
  - If a physical obstacle obstructs the gimbal or target is lost during a high-speed slew, the integrator accumulates huge values. When the target reappears, the gimbal experiences massive overshoot and violent runaway.

### 4.2 Watchdog Timer & Heartbeat Absence
- There is **no hardware or software watchdog** monitoring the tracking loop.
- If an unhandled exception occurs inside `BaselineTracker.process_frame()`:
  - In the Qt GUI, the `QTimer` stops ticking or logs to terminal; the PTZ controller retains its last commanded velocity indefinitely, driving the physical gimbal until it slams into mechanical limits.
  - In a production FSOC terminal, a missing frame watchdog MUST immediately command zero velocity and assert mechanical brakes within $\le 50\text{ ms}$.

---

## 5. Input Sanitization & Bounds Checking

| Component | Input Parameter | Validation in Code | Risk / Vulnerability |
| :--- | :--- | :--- | :--- |
| `OpticalSimulator` | `turbulence_cn2` | None (accepts negative values!) | Passing $C_n^2 < 0$ causes mathematical error in turbulence blur. |
| `OpticalSimulator` | `frame_rate` | None (accepts 0 or negative) | Causes `ZeroDivisionError` in $\Delta t = 1/\text{fps}$. |
| `PTZController` | `kp, ki, kd` | None | Negative gains create positive feedback instability; gimbal violently oscillates. |
| `ConfigManager` | YAML / JSON file | Basic Pydantic parsing | Malformed YAML can trigger unexpected parser exceptions on startup. |

---

## 6. Security & Reliability Remediation Recommendations

1. **Eliminate Headless Web Server from Flight Payload**: Remove FastAPI/Uvicorn/WebSockets from the real-time embedded tracking controller. Use deterministic serial/CAN/Ethernet (gRPC or zero-overhead UDP Protobuf) for telemetry.
2. **Implement Optical Beacon Frequency Modulation**: Do not track static brightness. Require beacon to be modulated at $10\text{--}100\text{ kHz}$ (or frame-rate synchronized square wave) so the tracker performs lock-in differential subtraction ($I_{\text{on}} - I_{\text{off}}$), rendering the system 100% immune to solar glints and continuous dazzlers.
3. **Hardware Watchdog & Deadman Failsafe**: Implement an asynchronous hardware deadman timer. If the tracking pipeline fails to refresh within $50\text{ ms}$, hardware logic automatically drives motor velocities to zero.
4. **PID Anti-Windup & Derivative Filtering**: Introduce back-calculation or conditional integration anti-windup to the PID controller to prevent gimbal runaway.
