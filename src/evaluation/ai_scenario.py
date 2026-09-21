"""
AI-Assisted Trajectory & Scenario Generation — Module 17 Subsystem.

Implements the AI-assisted experiment creation workflow:
  Natural Language Prompt
    │
    ▼
  AI Interpretation Engine (NLP Entity & Parameter Parser)
    │
    ▼
  Candidate Scenario Specification
    │
    ▼
  Scenario Specification Validator (Strict Physical & Boundary Checks)
    ├── REJECT if invalid (out-of-bounds, unphysical speed, invalid noise)
    └── ACCEPT if compliant
    │
    ▼
  Deterministic Trajectory Generator (Mathematical Formulation)
    │
    ▼
  Scenario JSON (Tagged with is_ai_generated=True)
    │
    ▼
  Simulator & Evaluation Harness (UUT Processing under Ground-Truth Firewall)

MANDATORY SAFETY RULES:
  1. AI output is NOT authoritative; validated specification is authoritative.
  2. The deterministic trajectory generator is authoritative.
  3. AI never directly controls or injects arbitrary coordinates into the simulator.
  4. Ground-truth firewall is strictly maintained.
  5. AI-generated scenarios are segregated from the official SIH standard benchmark suite.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.evaluation.harness import EvaluationHarness, EvaluationRunResult

logger = logging.getLogger(__name__)


# Supported trajectory types
SUPPORTED_TRAJECTORY_TYPES = {
    "CIRCULAR",
    "SPIRAL",
    "SINUSOIDAL",
    "FIGURE_8",
    "STRAIGHT_LINE",
    "RANDOM",
}


@dataclass
class CandidateScenarioSpec:
    """Raw, unvalidated candidate scenario specification extracted from NLP."""
    prompt: str
    trajectory_type: str = "CIRCULAR"
    target_speed: float = 50.0
    target_size: int = 10
    target_intensity: int = 220
    target_shape: str = "square"
    center_x: float = 1000.0
    center_y: float = 1000.0
    motion_params: Dict[str, Any] = field(default_factory=dict)
    atmospheric_condition: str = "CLEAR"
    atmos_params: Dict[str, Any] = field(default_factory=dict)
    noise_gaussian_enabled: bool = False
    noise_gaussian_sigma: float = 0.0
    noise_sp_enabled: bool = False
    noise_sp_density: float = 0.0
    noise_poisson_enabled: bool = False
    jitter_enabled: bool = False
    jitter_max_px: float = 0.0
    platform_motion_enabled: bool = False
    platform_motion_type: str = "LINEAR"
    platform_motion_max_px: float = 0.0
    duration_s: float = 30.0
    random_seed: int = 42
    description: str = ""


@dataclass(frozen=True)
class ValidatedScenarioSpec:
    """
    Authoritative, validated scenario specification that has passed all physical,
    continuity, and boundary constraints.
    """
    scenario_id: str
    prompt: str
    trajectory_type: str
    target_speed: float
    target_size: int
    target_intensity: int
    target_shape: str
    center_x: float
    center_y: float
    motion_params: Dict[str, Any]
    atmospheric_condition: str
    atmos_params: Dict[str, Any]
    noise_gaussian_enabled: bool
    noise_gaussian_sigma: float
    noise_sp_enabled: bool
    noise_sp_density: float
    noise_poisson_enabled: bool
    jitter_enabled: bool
    jitter_max_px: float
    platform_motion_enabled: bool
    platform_motion_type: str
    platform_motion_max_px: float
    duration_s: float
    random_seed: int
    description: str
    spec_hash: str
    timestamp: float = field(default_factory=time.time)
    is_ai_generated: bool = True

    def to_scenario_dict(self) -> Dict[str, Any]:
        """Converts into standard scenario JSON dictionary matching simulator schema."""
        m_params = dict(self.motion_params)
        m_type = self.trajectory_type.upper()
        if m_type == "LINEAR":
            m_type = "STRAIGHT_LINE"

        return {
            "scene": {
                "width": 2000,
                "height": 2000,
                "background_intensity": 30,
            },
            "camera": {
                "width": 640,
                "height": 480,
                "fov_h_deg": 4.0,
                "fov_v_deg": 3.0,
                "update_rate_hz": 30,
                "initial_x": self.center_x,
                "initial_y": self.center_y,
            },
            "target": {
                "count": 1,
                "size": self.target_size,
                "shape": self.target_shape,
                "intensity": self.target_intensity,
                "initial_position": "center",
                "initial_x": self.center_x,
                "initial_y": self.center_y,
                "speed": self.target_speed,
            },
            "motion": {
                "motion_type": m_type,
                "circle_radius": m_params.get("circle_radius", 200.0),
                "figure8_radius_x": m_params.get("figure8_radius_x", 250.0),
                "figure8_radius_y": m_params.get("figure8_radius_y", 150.0),
                "random_max_displacement": m_params.get("random_max_displacement", 10.0),
                "straight_line_angle_deg": m_params.get("straight_line_angle_deg", 45.0),
                "spiral_r0": m_params.get("spiral_r0", 30.0),
                "spiral_expansion_rate": m_params.get("spiral_expansion_rate", 8.0),
                "sinusoidal_amplitude": m_params.get("sinusoidal_amplitude", 80.0),
                "sinusoidal_frequency": m_params.get("sinusoidal_frequency", 0.3),
                "polygon_sides": m_params.get("polygon_sides", 4),
                "polygon_radius": m_params.get("polygon_radius", 180.0),
                "zigzag_width": m_params.get("zigzag_width", 400.0),
                "zigzag_height": m_params.get("zigzag_height", 200.0),
                "is_ai_generated": True,
                "ai_prompt": self.prompt,
            },
            "ptz": {
                "max_pan_speed_deg_s": 5.0,
                "max_tilt_speed_deg_s": 5.0,
                "update_rate_hz": 20,
                "proportional_gain": 8.0,
                "integral_gain": 2.0,
                "deadband_px": 1.0,
            },
            "noise": {
                "sp_enabled": self.noise_sp_enabled,
                "sp_density": self.noise_sp_density,
                "gaussian_enabled": self.noise_gaussian_enabled,
                "gaussian_sigma": self.noise_gaussian_sigma,
                "poisson_enabled": self.noise_poisson_enabled,
            },
            "atmospheric": {
                "condition": self.atmospheric_condition,
                "contrast_factor": self.atmos_params.get("contrast_factor"),
                "brightness_offset": self.atmos_params.get("brightness_offset"),
            },
            "jitter": {
                "enabled": self.jitter_enabled,
                "max_px_per_frame": self.jitter_max_px,
            },
            "platform_motion": {
                "enabled": self.platform_motion_enabled,
                "motion_type": self.platform_motion_type,
                "max_px_per_frame": self.platform_motion_max_px,
            },
            "simulation": {
                "duration_s": self.duration_s,
                "random_seed": self.random_seed,
                "mode": "SIMULATION",
                "mp4_path": None,
            },
            "logging": {
                "csv_enabled": True,
                "json_summary_enabled": True,
                "output_dir": "output",
            },
            "metadata": {
                "scenario_id": self.scenario_id,
                "is_ai_generated": True,
                "prompt": self.prompt,
                "spec_hash": self.spec_hash,
            },
        }


class ScenarioSpecificationValidator:
    """
    Authoritative validation engine for AI-generated scenario specifications.
    Enforces physical feasibility, bounding limits, and PS 26169 thresholds.
    """

    SCENE_WIDTH = 2000.0
    SCENE_HEIGHT = 2000.0
    SAFETY_MARGIN = 60.0

    @classmethod
    def validate(cls, candidate: CandidateScenarioSpec) -> Tuple[bool, Optional[ValidatedScenarioSpec], List[str]]:
        """
        Validates a candidate specification.

        Returns:
            Tuple: (is_valid, validated_spec, list_of_errors)
        """
        errors: List[str] = []

        # 1. Validate Trajectory Type
        t_type = candidate.trajectory_type.upper()
        if t_type == "LINEAR":
            t_type = "STRAIGHT_LINE"
        if t_type not in SUPPORTED_TRAJECTORY_TYPES:
            errors.append(
                f"Unsupported trajectory type: '{candidate.trajectory_type}'. "
                f"Supported: {sorted(list(SUPPORTED_TRAJECTORY_TYPES))}"
            )

        # 2. Validate Target Speed
        if candidate.target_speed <= 0.0:
            errors.append(f"Target speed must be strictly positive, got {candidate.target_speed} px/s.")
        elif candidate.target_speed > 120.0:
            errors.append(f"Target speed ({candidate.target_speed} px/s) exceeds maximum platform limit (120.0 px/s).")

        # 3. Validate Beacon Geometry & Intensity
        if candidate.target_size < 2 or candidate.target_size > 50:
            errors.append(f"Target size must be between 2 and 50 pixels, got {candidate.target_size}.")
        if candidate.target_intensity < 30 or candidate.target_intensity > 255:
            errors.append(f"Target intensity must be between 30 and 255, got {candidate.target_intensity}.")

        # 4. Validate Duration
        if candidate.duration_s < 1.0 or candidate.duration_s > 120.0:
            errors.append(f"Scenario duration must be between 1.0 and 120.0 seconds, got {candidate.duration_s}.")

        # 5. Validate Spatial Bounds
        cx = candidate.center_x
        cy = candidate.center_y
        if cx < cls.SAFETY_MARGIN or cx > cls.SCENE_WIDTH - cls.SAFETY_MARGIN:
            errors.append(f"Center X ({cx}) is out of safe scene bounds [{cls.SAFETY_MARGIN}, {cls.SCENE_WIDTH - cls.SAFETY_MARGIN}].")
        if cy < cls.SAFETY_MARGIN or cy > cls.SCENE_HEIGHT - cls.SAFETY_MARGIN:
            errors.append(f"Center Y ({cy}) is out of safe scene bounds [{cls.SAFETY_MARGIN}, {cls.SCENE_HEIGHT - cls.SAFETY_MARGIN}].")

        # Specific trajectory geometry checks
        m_params = candidate.motion_params
        if t_type in ("CIRCULAR", "SPIRAL"):
            r = m_params.get("circle_radius", 200.0)
            if r <= 0.0:
                errors.append(f"Circle radius must be strictly positive, got {r}.")
            max_allowed_r = min(cx, cy, cls.SCENE_WIDTH - cx, cls.SCENE_HEIGHT - cy) - cls.SAFETY_MARGIN
            if r > max_allowed_r:
                errors.append(f"Circle radius ({r} px) exceeds maximum safe radius ({max_allowed_r:.1f} px) for center ({cx}, {cy}).")

        if t_type == "SPIRAL":
            r0 = m_params.get("spiral_r0", 30.0)
            rate = m_params.get("spiral_expansion_rate", 8.0)
            if r0 <= 0.0 or rate < 0.0:
                errors.append(f"Spiral initial radius ({r0}) and expansion rate ({rate}) must be non-negative.")

        if t_type in ("POLYGON", "SQUARE", "PENTAGON"):
            sides = m_params.get("polygon_sides", 4 if t_type == "SQUARE" else 5)
            if sides < 3:
                errors.append(f"Polygon sides must be >= 3, got {sides}.")
            pr = m_params.get("polygon_radius", 180.0)
            if pr <= 0.0:
                errors.append(f"Polygon radius must be strictly positive, got {pr}.")

        # 6. Validate Disturbances against SIH PS 26169 hard limits
        if candidate.jitter_enabled:
            if candidate.jitter_max_px < 0.0 or candidate.jitter_max_px > 20.0:
                errors.append(f"Jitter max ({candidate.jitter_max_px} px/frame) exceeds PS 26169 limit (20.0 px/frame).")

        if candidate.platform_motion_enabled:
            if candidate.platform_motion_max_px < 0.0 or candidate.platform_motion_max_px > 20.0:
                errors.append(f"Platform motion max ({candidate.platform_motion_max_px} px/frame) exceeds PS 26169 limit (20.0 px/frame).")

        if candidate.noise_gaussian_enabled:
            if candidate.noise_gaussian_sigma < 0.0 or candidate.noise_gaussian_sigma > 20.0:
                errors.append(f"Gaussian noise sigma ({candidate.noise_gaussian_sigma}) exceeds PS 26169 limit (20.0).")

        if candidate.noise_sp_enabled:
            if candidate.noise_sp_density < 0.0 or candidate.noise_sp_density > 0.20:
                errors.append(f"Salt & pepper density ({candidate.noise_sp_density}) exceeds maximum safe threshold (0.20).")

        # 7. Reject if any error found
        if errors:
            return False, None, errors

        # 8. Compute deterministic spec digest and instantiate ValidatedScenarioSpec
        spec_repr = f"{candidate.prompt}_{t_type}_{candidate.target_speed}_{candidate.random_seed}_{json.dumps(m_params, sort_keys=True)}"
        spec_hash = hashlib.sha256(spec_repr.encode("utf-8")).hexdigest()[:12]
        scenario_id = f"ai_{t_type.lower()}_{spec_hash}"

        validated = ValidatedScenarioSpec(
            scenario_id=scenario_id,
            prompt=candidate.prompt,
            trajectory_type=t_type,
            target_speed=candidate.target_speed,
            target_size=candidate.target_size,
            target_intensity=candidate.target_intensity,
            target_shape=candidate.target_shape,
            center_x=candidate.center_x,
            center_y=candidate.center_y,
            motion_params=candidate.motion_params,
            atmospheric_condition=candidate.atmospheric_condition,
            atmos_params=candidate.atmos_params,
            noise_gaussian_enabled=candidate.noise_gaussian_enabled,
            noise_gaussian_sigma=candidate.noise_gaussian_sigma,
            noise_sp_enabled=candidate.noise_sp_enabled,
            noise_sp_density=candidate.noise_sp_density,
            noise_poisson_enabled=candidate.noise_poisson_enabled,
            jitter_enabled=candidate.jitter_enabled,
            jitter_max_px=candidate.jitter_max_px,
            platform_motion_enabled=candidate.platform_motion_enabled,
            platform_motion_type=candidate.platform_motion_type,
            platform_motion_max_px=candidate.platform_motion_max_px,
            duration_s=candidate.duration_s,
            random_seed=candidate.random_seed,
            description=candidate.description or f"AI-assisted scenario: '{candidate.prompt}'",
            spec_hash=spec_hash,
        )

        return True, validated, []


class AIInterpretationEngine:
    """
    Translates unstructured natural-language requests into structured CandidateScenarioSpecs.
    Uses robust NLP token parsing, numerical regex matching, and domain heuristics.
    """

    @classmethod
    def interpret(cls, prompt: str, default_seed: int = 42) -> CandidateScenarioSpec:
        """
        Parses user prompt into CandidateScenarioSpec.
        """
        p_lower = prompt.lower().strip()

        # 1. Infer Trajectory Type
        t_type = "CIRCULAR"
        m_params: Dict[str, Any] = {}

        if any(w in p_lower for w in ("spiral", "expanding radius", "increasing radius", "helix", "vortex")):
            t_type = "SPIRAL"
            m_params["spiral_r0"] = 35.0
            m_params["spiral_expansion_rate"] = 10.0
            m_params["circle_radius"] = 220.0
        elif any(w in p_lower for w in ("sinusoid", "sine", "wave", "undulat")):
            t_type = "SINUSOIDAL"
            m_params["sinusoidal_amplitude"] = 80.0
            m_params["sinusoidal_frequency"] = 0.35
        elif any(w in p_lower for w in ("figure 8", "figure-8", "figure8", "infinity", "lemniscate")):
            t_type = "FIGURE_8"
            m_params["figure8_radius_x"] = 250.0
            m_params["figure8_radius_y"] = 140.0
        elif any(w in p_lower for w in ("linear", "straight", "line", "crossing", "horizontal", "diagonal")):
            t_type = "STRAIGHT_LINE"
            m_params["straight_line_angle_deg"] = 35.0
        elif any(w in p_lower for w in ("random", "stochastic", "brownian", "erratic")):
            t_type = "RANDOM"
            m_params["random_max_displacement"] = 12.0
        elif any(w in p_lower for w in ("circle", "circular", "orbit", "round")):
            t_type = "CIRCULAR"
            m_params["circle_radius"] = 200.0

        # 2. Infer Target Speed
        speed = 50.0  # nominal default
        # Check explicit numbers, e.g. "40 px/s" or "speed 65"
        speed_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:px/s|pixels?/sec|speed)", p_lower)
        if speed_match:
            speed = float(speed_match.group(1))
        elif any(w in p_lower for w in ("high speed", "fast", "rapid", "quick")):
            speed = 75.0
        elif any(w in p_lower for w in ("slow", "gentle", "crawling")):
            speed = 25.0
        elif any(w in p_lower for w in ("moderate", "nominal", "medium")):
            speed = 50.0

        # 3. Infer Beacon Size & Intensity
        target_size = 10
        if any(w in p_lower for w in ("small", "tiny", "dim spot")):
            target_size = 6
        elif any(w in p_lower for w in ("large", "big", "huge")):
            target_size = 16

        target_intensity = 220
        if any(w in p_lower for w in ("dim", "faint", "weak")):
            target_intensity = 120
        elif any(w in p_lower for w in ("bright", "saturated", "intense")):
            target_intensity = 255

        # 4. Infer Atmospheric Conditions
        atmos_cond = "CLEAR"
        atmos_params: Dict[str, Any] = {}
        if "fog" in p_lower:
            atmos_cond = "FOG"
            atmos_params = {"contrast_factor": 0.4, "brightness_offset": 40}
        elif "haze" in p_lower:
            atmos_cond = "HAZE"
            atmos_params = {"contrast_factor": 0.6, "brightness_offset": 25}
        elif "rain" in p_lower:
            atmos_cond = "RAIN"
            atmos_params = {"contrast_factor": 0.7, "brightness_offset": 15}
        elif any(w in p_lower for w in ("night", "low light", "dark")):
            atmos_cond = "LOW_LIGHT"
            atmos_params = {"contrast_factor": 0.45, "brightness_offset": -30}

        # 5. Infer Sensor Noise & Jitter Disturbances
        gaussian_enabled = False
        gaussian_sigma = 0.0
        if any(w in p_lower for w in ("gaussian", "sensor noise", "electronic noise", "noisy")):
            gaussian_enabled = True
            gaussian_sigma = 12.0

        sp_enabled = False
        sp_density = 0.0
        if any(w in p_lower for w in ("salt and pepper", "s&p", "impulse noise", "dead pixels")):
            sp_enabled = True
            sp_density = 0.07

        poisson_enabled = bool("poisson" in p_lower or "shot noise" in p_lower)

        jitter_enabled = False
        jitter_max_px = 0.0
        if any(w in p_lower for w in ("jitter", "vibration", "shaking")):
            jitter_enabled = True
            jitter_max_px = 5.0 if "severe" in p_lower or "high" in p_lower else 3.0

        platform_enabled = False
        platform_max_px = 0.0
        if any(w in p_lower for w in ("platform motion", "attitude drift", "vehicle drift", "drift")):
            platform_enabled = True
            platform_max_px = 4.0

        return CandidateScenarioSpec(
            prompt=prompt,
            trajectory_type=t_type,
            target_speed=speed,
            target_size=target_size,
            target_intensity=target_intensity,
            center_x=1000.0,
            center_y=1000.0,
            motion_params=m_params,
            atmospheric_condition=atmos_cond,
            atmos_params=atmos_params,
            noise_gaussian_enabled=gaussian_enabled,
            noise_gaussian_sigma=gaussian_sigma,
            noise_sp_enabled=sp_enabled,
            noise_sp_density=sp_density,
            noise_poisson_enabled=poisson_enabled,
            jitter_enabled=jitter_enabled,
            jitter_max_px=jitter_max_px,
            platform_motion_enabled=platform_enabled,
            platform_motion_type="LINEAR",
            platform_motion_max_px=platform_max_px,
            duration_s=30.0,
            random_seed=default_seed,
            description=f"Generated from: '{prompt}'",
        )


class DeterministicTrajectoryGenerator:
    """
    Mathematical trajectory compiler.
    Converts ValidatedScenarioSpec into reproducible scenario JSON on disk.
    """

    @classmethod
    def generate_scenario_json(
        cls,
        spec: ValidatedScenarioSpec,
        output_dir: str = "scenarios/ai_generated",
    ) -> str:
        """
        Serializes validated specification into scenario JSON artifact.
        Guarantees deterministic replay: same spec + seed = identical file contents.

        Returns:
            Path to created scenario JSON file.
        """
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{spec.scenario_id}.json")

        scenario_dict = spec.to_scenario_dict()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(scenario_dict, f, indent=2)

        logger.info(f"AI-assisted scenario serialized to: '{file_path}'")
        return file_path


class AIScenarioWorkflow:
    """
    Orchestrates the complete AI Scenario Creation & Evaluation Workflow:
      Prompt -> Interpret -> Validate -> Generate -> Evaluate.
    """

    def __init__(self, harness: EvaluationHarness) -> None:
        self.harness = harness

    def execute_prompt(
        self,
        prompt: str,
        algorithm_name: str = "baseline_tracker",
        seed: int = 42,
        max_frames: int = 60,
        output_dir: Optional[str] = None,
    ) -> Tuple[bool, Optional[ValidatedScenarioSpec], Optional[EvaluationRunResult], List[str]]:
        """
        Executes an end-to-end AI-assisted scenario experiment.

        Returns:
            Tuple: (success, validated_spec, evaluation_run_result, error_messages)
        """
        from src.evaluation.harness import EvaluationExperiment

        target_out = output_dir or os.path.join("output", "ai_scenarios")
        os.makedirs(target_out, exist_ok=True)

        # 1. NLP Interpretation
        candidate = AIInterpretationEngine.interpret(prompt, default_seed=seed)

        # 2. Strict Physical & Boundary Validation
        is_valid, validated_spec, errors = ScenarioSpecificationValidator.validate(candidate)
        if not is_valid or validated_spec is None:
            logger.warning(f"AI scenario rejected by validator for prompt '{prompt}': {errors}")
            return False, None, None, errors

        # 3. Deterministic Trajectory & Scenario Generation
        scenario_dir = os.path.join(target_out, "scenarios")
        scenario_path = DeterministicTrajectoryGenerator.generate_scenario_json(
            validated_spec,
            output_dir=scenario_dir,
        )

        # 4. Evaluation Execution via Harness
        exp = EvaluationExperiment(
            experiment_id=f"ai_eval_{validated_spec.scenario_id}",
            algorithm_name=algorithm_name,
            source_type="SIMULATION",
            scenario_path=scenario_path,
            random_seed=seed,
            max_frames=max_frames,
            output_dir=os.path.join(target_out, validated_spec.scenario_id),
        )

        logger.info(f"Evaluating AI scenario '{validated_spec.scenario_id}' with '{algorithm_name}'...")
        res = self.harness.run_experiment(exp)

        return True, validated_spec, res, []
