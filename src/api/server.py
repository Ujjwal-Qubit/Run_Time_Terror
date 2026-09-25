"""
LumiTrack FastAPI Backend Server — Client-Server Web Adapter.
Exposes REST endpoints and real-time WebSocket stream for the LumiTrack Web Frontend.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager, SystemConfig
from src.evaluation.benchmark_manager import BenchmarkManager
from src.evaluation.reporting import ComprehensiveReportGenerator
from src.evaluation.ai_scenario import AIScenarioWorkflow
from src.frame.data_contracts import FrameSource, TrackingState

logger = logging.getLogger("lumitrack.api")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LumiTrack API Server",
    description="Backend API and WebSocket Stream for LumiTrack FSOC Tracking & Evaluation Platform",
    version="1.0.0",
)

# CORS configuration:
# For local dev the wildcard is acceptable.
# In production, set LUMITRACK_CORS_ORIGINS env var to a comma-separated list:
#   LUMITRACK_CORS_ORIGINS=https://lumitrack.example.com
_cors_origins_raw = os.environ.get("LUMITRACK_CORS_ORIGINS", "*")
_cors_origins: list = (
    [o.strip() for o in _cors_origins_raw.split(",")]
    if _cors_origins_raw != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # credentials=True requires explicit origins, not "*"
    allow_credentials=(_cors_origins != ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global AppController and BenchmarkManager instances
controller: AppController = AppController()
benchmark_mgr: BenchmarkManager = BenchmarkManager(controller)

# Lock for synchronizing state modifications
state_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class AlgorithmSelectRequest(BaseModel):
    algorithm_name: str

class MatrixRunRequest(BaseModel):
    subset: str = "CORE"
    algorithm: Optional[str] = None
    seed: int = 42
    max_frames: Optional[int] = None

class AIScenarioRequest(BaseModel):
    prompt: str
    algorithm: Optional[str] = None
    seed: int = 42
    max_frames: int = 60

class ConfigUpdateRequest(BaseModel):
    camera: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None
    motion: Optional[Dict[str, Any]] = None
    atmospheric: Optional[Dict[str, Any]] = None
    noise: Optional[Dict[str, Any]] = None
    jitter: Optional[Dict[str, Any]] = None
    platform_motion: Optional[Dict[str, Any]] = None
    ptz: Optional[Dict[str, Any]] = None
    simulation: Optional[Dict[str, Any]] = None
    local_contrast: Optional[Dict[str, Any]] = None
    beacons: Optional[List[Dict[str, Any]]] = None

# ---------------------------------------------------------------------------
# REST Endpoints: Algorithms
# ---------------------------------------------------------------------------

@app.get("/api/v1/algorithms")
def get_algorithms() -> Dict[str, Any]:
    """Returns list of discovered tracking algorithms and their manifests."""
    try:
        discovered = controller.discover_algorithms()
        algorithms_list = []
        for name, meta in discovered.items():
            algorithms_list.append({
                "name": name,
                "version": meta.manifest.version,
                "description": meta.manifest.description,
                "author": meta.manifest.author,
                "api_version": meta.manifest.api_version,
                "dependencies": meta.manifest.dependencies,
                "metadata": meta.manifest.metadata,
                "status": "Ready" if controller.active_algorithm_name != name else ("Active" if not controller.algorithm_error else "Error")
            })
        return {
            "algorithms": algorithms_list,
            "active_algorithm": controller.active_algorithm_name or "baseline_tracker",
            "error": controller.algorithm_error,
        }
    except Exception as e:
        logger.error(f"Error fetching algorithms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/algorithms/select")
def select_algorithm(req: AlgorithmSelectRequest) -> Dict[str, Any]:
    """Activates a specific algorithm plugin."""
    with state_lock:
        success = controller.select_algorithm(req.algorithm_name)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=controller.algorithm_error or f"Failed to select algorithm '{req.algorithm_name}'"
            )
        return {
            "success": True,
            "active_algorithm": controller.active_algorithm_name,
            "error": controller.algorithm_error,
        }

# ---------------------------------------------------------------------------
# REST Endpoints: Scenarios & Configurations
# ---------------------------------------------------------------------------

@app.get("/api/v1/scenarios")
def get_scenarios() -> Dict[str, Any]:
    """Returns list of available predefined scenario JSON files."""
    scenarios_dir = Path("scenarios")
    scenarios = []
    if scenarios_dir.is_dir():
        for f in sorted(scenarios_dir.glob("*.json")):
            scenarios.append(f.name)
    return {"scenarios": scenarios}


@app.get("/api/v1/config")
def get_config() -> Dict[str, Any]:
    """Returns the current SystemConfig JSON."""
    return controller.config_manager.config.to_dict()


@app.put("/api/v1/config")
def update_config(req: ConfigUpdateRequest) -> Dict[str, Any]:
    """Updates system configuration dynamically with partial updates."""
    with state_lock:
        cfg = controller.config_manager.config
        data = req.dict(exclude_unset=True)
        unknown_fields: List[str] = []

        for section, values in data.items():
            if section == "beacons" and isinstance(values, list):
                # Multi-beacon list — handled specially
                from src.config.config_manager import BeaconConfig as _BeaconConfig
                cfg.beacons = [
                    _BeaconConfig(**{k: v for k, v in b.items() if k in _BeaconConfig.__dataclass_fields__})
                    for b in values
                ]
                # Validate the beacon list
                errs = controller.config_manager.validate()
                beacon_errs = [e for e in errs if "beacon" in e.lower() or "primary" in e.lower() or "secondary" in e.lower()]
                if beacon_errs:
                    raise HTTPException(status_code=400, detail="; ".join(beacon_errs))
            elif hasattr(cfg, section) and isinstance(values, dict):
                sec_obj = getattr(cfg, section)
                for k, v in values.items():
                    if hasattr(sec_obj, k):
                        setattr(sec_obj, k, v)
                    else:
                        unknown_fields.append(f"{section}.{k}")
            elif not hasattr(cfg, section):
                unknown_fields.append(section)

        if unknown_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown config field(s): {', '.join(unknown_fields)}"
            )

        # Apply live changes if running in simulation
        if controller.is_running and cfg.simulation.mode == "SIMULATION":
            if controller.target_manager:
                controller.target_manager._target_cfg = cfg.target
                controller.target_manager._motion_cfg = cfg.motion
            if controller.disturbance_engine:
                controller.disturbance_engine._atmos_cfg = cfg.atmospheric
                controller.disturbance_engine._noise_cfg = cfg.noise
                controller.disturbance_engine._jitter_cfg = cfg.jitter
                controller.disturbance_engine._platform_cfg = cfg.platform_motion
                # Local contrast disturbance (new field — safe to set if attribute exists)
                if hasattr(controller.disturbance_engine, '_local_contrast_cfg'):
                    controller.disturbance_engine._local_contrast_cfg = cfg.local_contrast

        return {"success": True, "updated_config": cfg.to_dict()}


@app.post("/api/v1/scenarios/load")
def load_scenario(name: str) -> Dict[str, Any]:
    """Loads a named scenario from scenarios/ directory."""
    if not name.endswith(".json"):
        name += ".json"
    path = Path("scenarios") / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found.")
    with state_lock:
        controller.config_manager.load_from_file(str(path))
        return {"success": True, "scenario": name, "config": controller.config_manager.config.to_dict()}

class ScenarioSaveRequest(BaseModel):
    name: str

@app.post("/api/v1/scenarios/save")
def save_scenario(req: ScenarioSaveRequest) -> Dict[str, Any]:
    """Saves the current configuration as a new scenario."""
    name = req.name
    if not name.endswith(".json"):
        name += ".json"
    path = Path("scenarios") / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with state_lock:
        cfg_dict = controller.config_manager.config.to_dict()
        with open(path, "w") as f:
            json.dump(cfg_dict, f, indent=2)
        return {"success": True, "scenario": name}

@app.delete("/api/v1/scenarios/{name}")
def delete_scenario(name: str) -> Dict[str, Any]:
    """Deletes a scenario."""
    if not name.endswith(".json"):
        name += ".json"
    path = Path("scenarios") / name
    if path.is_file():
        path.unlink()
        return {"success": True}
    raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found.")

# ---------------------------------------------------------------------------
# REST Endpoints: Simulation Lifecycle Controls
# ---------------------------------------------------------------------------

@app.post("/api/v1/simulation/start")
def start_simulation() -> Dict[str, Any]:
    """Initializes and starts the simulation / playback loop."""
    with state_lock:
        try:
            # Interactive runs default to indefinite duration
            controller.config_manager.config.simulation.duration_s = None
            controller.initialize()
            controller.start_background_loop()
            return {"status": "RUNNING", "mode": controller.config_manager.config.simulation.mode}
        except Exception as e:
            logger.error(f"Error starting simulation: {e}")
            raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/simulation/stop")
def stop_simulation() -> Dict[str, Any]:
    """Stops the active simulation loop."""
    with state_lock:
        controller.stop()
        return {"status": "IDLE"}


@app.post("/api/v1/simulation/pause")
def pause_simulation() -> Dict[str, Any]:
    """Pauses the simulation loop without clearing buffers."""
    with state_lock:
        controller.pause()
        return {"status": "PAUSED"}


@app.post("/api/v1/simulation/resume")
def resume_simulation() -> Dict[str, Any]:
    """Resumes paused simulation."""
    with state_lock:
        controller.resume()
        return {"status": "RUNNING"}


@app.post("/api/v1/simulation/reset")
def reset_simulation() -> Dict[str, Any]:
    """Flushes filters, resets camera, clears telemetry and queues."""
    with state_lock:
        controller.reset()
        return {"status": "IDLE"}


@app.get("/api/v1/simulation/status")
def get_simulation_status() -> Dict[str, Any]:
    """Returns current runtime state."""
    state = "IDLE"
    if controller.is_running:
        state = "PAUSED" if controller.is_paused else "RUNNING"
    return {
        "status": state,
        "mode": controller.config_manager.config.simulation.mode,
        "frame_count": controller.frame_count,
        "active_algorithm": controller.active_algorithm_name,
        "algorithm_error": controller.algorithm_error,
    }

# ---------------------------------------------------------------------------
# REST Endpoints: Evaluation & Benchmarks
# ---------------------------------------------------------------------------

@app.post("/api/v1/evaluation/matrix")
def run_benchmark_matrix(req: MatrixRunRequest) -> Dict[str, Any]:
    """Executes standard benchmark matrix subset."""
    algo = req.algorithm or controller.active_algorithm_name or "baseline_tracker"
    try:
        bm = BenchmarkManager(controller)
        results = bm.run_benchmark_matrix(
            subset=req.subset,
            algorithms=[algo],
            random_seed=req.seed,
            max_frames=req.max_frames or 30,
            output_dir="output/matrix",
        )
        j_p, c_p, m_p = bm.generate_comprehensive_report(results, output_dir="output/matrix")
        
        # Read the generated JSON report
        report_data = {}
        if os.path.isfile(j_p):
            with open(j_p, "r", encoding="utf-8") as f:
                report_data = json.load(f)

        return {
            # Canonical identifier — prefer suite_id; batch_id kept as alias
            "suite_id": results.suite_id,
            "batch_id": results.suite_id,   # backward-compat alias
            "status": "COMPLETED",
            "passed_sih_spec": results.passed_sih_spec,
            "verdict": "PASS" if results.passed_sih_spec else "FAIL",
            "mean_fps": results.mean_algorithm_fps,
            "mean_rmse": results.mean_rmse_centroid,
            # mean_target_loss_rate is a fraction (0.0-1.0); frontend converts to %
            "mean_loss_rate": results.mean_target_loss_rate,
            "report_paths": {"json": j_p, "csv": c_p, "markdown": m_p},
            "report_data": report_data,
        }
    except Exception as e:
        logger.error(f"Matrix run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/evaluation/ai-scenario")
def run_ai_scenario(req: AIScenarioRequest) -> Dict[str, Any]:
    """Generates and executes a deterministic scenario from a natural language prompt."""
    algo = req.algorithm or controller.active_algorithm_name or "baseline_tracker"
    try:
        from src.evaluation.harness import EvaluationHarness
        workflow = AIScenarioWorkflow(EvaluationHarness(controller))
        outcome = workflow.execute_prompt(
            prompt=req.prompt,
            algorithm_name=algo,
            seed=req.seed,
            max_frames=req.max_frames,
            output_dir="output/ai_scenarios",
        )

        return {
            "scenario_id": outcome.scenario_definition.scenario_id,
            "valid": outcome.validation_result.valid,
            "validation_errors": outcome.validation_result.errors,
            "spec": outcome.scenario_definition.to_dict() if outcome.scenario_definition else {},
            "evaluation": {
                "algorithm_fps": outcome.evaluation_result.algorithm_fps if outcome.evaluation_result else None,
                "centroid_rmse": outcome.evaluation_result.centroid_rmse if outcome.evaluation_result else None,
                "target_loss_rate": outcome.evaluation_result.target_loss_rate if outcome.evaluation_result else None,
                "acquisition_time_s": outcome.evaluation_result.acquisition_time_s if outcome.evaluation_result else None,
                "passed_sih_spec": outcome.evaluation_result.passed_sih_spec if outcome.evaluation_result else False,
            } if outcome.evaluation_result else None,
            "report_path": outcome.report_path,
        }
    except Exception as e:
        logger.error(f"AI Scenario generation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/v1/reports/latest")
def get_latest_report() -> Dict[str, Any]:
    """Scans output/ directory for the most recently generated JSON report."""
    output_dir = Path("output")
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="No output directory found.")

    json_files = list(output_dir.glob("**/*_report.json")) + list(output_dir.glob("**/*_summary.json"))
    if not json_files:
        raise HTTPException(status_code=404, detail="No report files found. Run a benchmark first.")

    latest_file = max(json_files, key=os.path.getmtime)
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "filename": latest_file.name,
        "path": str(latest_file),
        "data": data,
    }


@app.get("/api/v1/reports/list")
def list_reports() -> Dict[str, Any]:
    """Returns list of all reports in output/ directory."""
    output_dir = Path("output")
    reports = []
    if output_dir.exists():
        for path in sorted(output_dir.glob("**/*"), key=os.path.getmtime, reverse=True):
            if path.is_file() and path.suffix in [".json", ".csv", ".md"]:
                reports.append({
                    "name": path.name,
                    "rel_path": str(path.relative_to(output_dir)),
                    "type": path.suffix[1:].upper(),
                    "size_bytes": path.stat().st_size,
                    "mtime": path.stat().st_mtime,
                })
    return {"reports": reports}

# ---------------------------------------------------------------------------
# Realtime Streaming WebSocket Endpoint (/ws/live)
# ---------------------------------------------------------------------------

@app.websocket("/ws/live")
async def websocket_live_stream(websocket: WebSocket):
    """
    Streams 30 FPS VisualizationPacket payloads to the client.
    Payload includes image_base64 (JPEG), lock status, coordinates, angles, and telemetry.
    """
    await websocket.accept()
    logger.info("WebSocket client connected to /ws/live")

    try:
        while True:
            # Non-blocking poll for incoming client control messages (e.g. ping)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.001)
                # Handle optional client message if sent
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            # Drain freshest VisualizationState from controller
            state = controller.get_latest_visualization_state()
            if state is not None and state.display_image is not None:
                # Encode display image to JPEG base64
                img = state.display_image
                if img.ndim == 2:
                    # Grayscale uint8 -> Convert to BGR for JPEG encoding
                    bgr_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                else:
                    bgr_img = img

                # Encode JPEG with quality 85 for high speed + fidelity
                success, buf = cv2.imencode(".jpg", bgr_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                img_b64 = ""
                if success:
                    img_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

                # Derive lock status
                is_tracking = state.tracking_state == "TRACKING"
                is_acquiring = state.tracking_state in ["ACQUIRING", "REACQUIRING"]
                lock_status = "LOCKED" if is_tracking else ("ACQUIRING" if is_acquiring else "UNLOCKED")

                # Compute tracking error relative to frame center (boresight)
                h, w = img.shape[:2]
                cx, cy = w / 2.0, h / 2.0
                trk_err = None
                if state.estimated_centroid_x is not None and state.estimated_centroid_y is not None:
                    dx = state.estimated_centroid_x - cx
                    dy = state.estimated_centroid_y - cy
                    trk_err = round(float(np.sqrt(dx * dx + dy * dy)), 2)

                packet = {
                    "frame_number": state.frame_number,
                    "timestamp": round(float(state.timestamp), 3),
                    "tracking_state": state.tracking_state,
                    "lock_status": lock_status,
                    "estimated_centroid": {
                        "x": round(float(state.estimated_centroid_x), 2),
                        "y": round(float(state.estimated_centroid_y), 2)
                    } if state.estimated_centroid_x is not None else None,
                    "ground_truth": {
                        "x": round(float(state.ground_truth_x), 2),
                        "y": round(float(state.ground_truth_y), 2)
                    } if state.ground_truth_x is not None else None,
                    "roi": {
                        "x": state.roi.x,
                        "y": state.roi.y,
                        "w": state.roi.width,
                        "h": state.roi.height
                    } if state.roi else None,
                    "pan_angle_deg": round(float(state.pan_angle_deg), 3),
                    "tilt_angle_deg": round(float(state.tilt_angle_deg), 3),
                    "camera_fov": float(state.camera_fov),
                    "tracking_error_px": trk_err,
                    "fps": round(float(state.fps), 1),
                    "latency_ms": round(float(state.processing_latency_ms), 2),
                    "resolution": {"width": w, "height": h},
                    "image_base64": img_b64,
                }
                await websocket.send_json(packet)

            await asyncio.sleep(0.033)  # Target ~30 FPS
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# ---------------------------------------------------------------------------
# Static frontend mounting (Production)
# ---------------------------------------------------------------------------

frontend_dist = Path("frontend/dist")
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
