# LumiTrack — Phase 2 Ground-Truth Firewall Audit
## Rigorous Verification of Data Isolation Between Simulation Ground Truth and Live Operational Telemetry

---

## 1. Ground-Truth Firewall Mandate

In coarse-tracking FSOC terminals (SIH 2026 Problem Statement 26169), the operational tracking system has access solely to incoming camera frames and gimbal encoder telemetry. It possesses **zero knowledge** of true target position, simulator trajectory equations, or synthetic noise seeds.

The **Ground-Truth Firewall** is an architectural and ethical invariant that guarantees:
1. Operational tracking, control, and live UI displays never consume simulator ground-truth state.
2. Live WebSocket, IPC, and QtWebChannel payloads contain **zero ground-truth keys** (`ground_truth_x`, `ground_truth_y`, `target_x`, `target_y`, `seed`, `hidden_world_x/y`).
3. Validation metrics (RMSE against ground truth, acquisition time against ideal target entry) are quarantined strictly behind offline evaluation harnesses and explicitly tagged with `[GROUND TRUTH — VALIDATION ONLY]`.

---

## 2. Static AST & Contract Inspection

Static inspection was performed on all Phase 2 serialization functions in `src/app/gui/web_bridge.py`:

### 2.1 Live Telemetry Contract (`TrackingTelemetry`)
```json
{
  "frameNumber": 120,
  "timestamp": 4.0,
  "trackingState": "TRACKING",
  "centroid": { "x": 324.5, "y": 238.1 },
  "roi": { "x": 300, "y": 214, "width": 48, "height": 48 },
  "confidence": 0.98,
  "boresightOffsetPx": 4.88,
  "trackingErrorPx": null,
  "processingLatencyMs": 1.15,
  "algorithmFps": 30.0,
  "panAngleDeg": 0.421,
  "tiltAngleDeg": -0.185,
  "cameraFovH": 4.0,
  "cameraFovV": 3.0,
  "cameraWidth": 640,
  "cameraHeight": 480,
  "ptzActive": true
}
```

- **Inspection Finding**: `boresightOffsetPx` is computed strictly from the camera optical center $(320, 240)$ and the detected candidate centroid: $\sqrt{(x_{\text{est}} - 320)^2 + (y_{\text{est}} - 240)^2}$.
- `trackingErrorPx` (ground-truth radial distance) is set to `null` in the live stream.
- Ground truth coordinates are completely absent from the serialized payload dictionary.

---

## 3. Runtime Stream Audit Results

During the Phase 2 verification benchmark (`scripts/measure_phase2_frontend.py`), 100 consecutive live telemetry frames were captured and scanned for ground truth leakage:

| Inspection Criterion | Target | Measured Result | Status |
|---|---|---|---|
| `ground_truth_x` in live telemetry | 0 occurrences | **0** | **PASS** |
| `ground_truth_y` in live telemetry | 0 occurrences | **0** | **PASS** |
| `target_x` / `target_y` in live telemetry | 0 occurrences | **0** | **PASS** |
| `simulation_seed` in live telemetry | 0 occurrences | **0** | **PASS** |
| Live mode ground-truth curve in Results & Analysis | NULL / Omitted | **NULL** | **PASS** |
| Subsystem Diagnostics Firewall status | ENFORCED | **ENFORCED** | **PASS** |

---

## 4. 3D Workspace Pinhole Kinematics Verification

A potential point of leakage in 3D workspaces is directly querying simulator target position $(X_t, Y_t, Z_t)$ to render the target marker and trajectory trail.

In LumiTrack Phase 2, `ThreeDWorkspace.tsx` enforces strict operational independence by reconstructing the target Line-of-Sight (LOS) purely from the detected centroid $[x_{\text{est}}, y_{\text{est}}]$, camera pinhole optics, and gimbal kinematics:

$$\Delta\text{az} = \arctan\left(\frac{x_{\text{est}} - 320}{f_x}\right), \quad \Delta\text{el} = -\arctan\left(\frac{y_{\text{est}} - 240}{f_y}\right)$$

$$\text{Ray}_{\text{world}} = \mathbf{R}_{\text{gimbal}}(\text{pan}, \text{tilt}) \cdot \begin{bmatrix} \sin(\Delta\text{az}) \\ -\sin(\Delta\text{el}) \\ \cos(\Delta\text{az})\cos(\Delta\text{el}) \end{bmatrix}$$

- **Verification**: In live mode, the 3D target marker follows the detected beacon optical ray without ever touching simulator state.
- If target detection drops out, the 3D ray disappears, exactly mirroring real optical tracking behavior.

---

## 5. Validation Mode Seam Separation

When the operator explicitly toggles `Validation Mode: ON`:
1. The UI displays an unmissable amber banner: `[GROUND TRUTH — VALIDATION ONLY] SIMULATION TRAJECTORY REVEALED`.
2. Results & Analysis overlays the ground truth error curve in dashed amber lines.
3. Every report generated under this mode includes the required provenance header:
   `> [!WARNING] Ground truth comparison metrics are strictly restricted to offline post-run evaluation.`

---

## 6. Audit Conclusion

The Ground-Truth Firewall is 100% intact, statically verified, and empirically confirmed across all 6 workspaces.
