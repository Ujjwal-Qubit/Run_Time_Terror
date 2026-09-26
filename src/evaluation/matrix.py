"""
Standard Benchmark Matrix — Module 17 Subsystem.

Defines the reproducible, objective benchmark scenario matrix covering all
operational dimensions specified in SIH Problem Statement 26169:
  1. Motion patterns: Straight line, Circular, Figure-8, Random walk
  2. Kinematic & scale stress: High speed, Small/Dim target, Large/Saturated target
  3. Atmospheric degradation: Clear, Haze, Fog, Rain, Low-light
  4. Sensor noise: Gaussian sensor noise, Salt & Pepper impulse noise, Poisson shot noise
  5. Geometric disturbances: Camera jitter, Platform motion drift
  6. Combined FSOC disturbances: Multi-hazard environmental stress scenarios

Supports configurable benchmark subsets (SMOKE, CORE, DISTURBANCE, FULL),
deterministic replay across runs, and multi-algorithm execution.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.evaluation.harness import EvaluationHarness, EvaluationRunResult

logger = logging.getLogger(__name__)


class BenchmarkSubset(str, enum.Enum):
    """Configurable subsets of the standard benchmark matrix."""
    SMOKE = "SMOKE"                # 3 fast scenarios (~30-50 frames) for sanity/smoke testing
    CORE = "CORE"                  # 6 primary SIH validation scenarios
    DISTURBANCE = "DISTURBANCE"    # 8 disturbance sweep scenarios
    FULL = "FULL"                  # All 19 standard scenarios in the matrix


@dataclass
class BenchmarkScenarioDefinition:
    """
    Formal specification for a reproducible benchmark scenario.
    Maps directly to the simulation engine and scenario schema.
    """
    scenario_id: str
    name: str
    category: str                  # MOTION, KINEMATICS, ATMOSPHERIC, NOISE, GEOMETRIC, COMBINED, EXTERNAL_MP4
    description: str
    source_type: str = "SIMULATION" # SIMULATION or MP4
    motion_type: str = "CIRCULAR"  # STRAIGHT_LINE, CIRCULAR, FIGURE_8, RANDOM
    target_speed: float = 50.0     # pixels/second
    target_size: int = 10          # beacon pixel dimension
    target_shape: str = "square"   # square, circle, gaussian
    target_intensity: int = 220    # 0-255 peak intensity
    motion_params: Dict[str, Any] = field(default_factory=dict)
    atmospheric_condition: str = "CLEAR" # CLEAR, HAZE, FOG, RAIN, LOW_LIGHT
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
    default_frames: int = 100
    duration_s: float = 30.0
    mp4_path: Optional[str] = None
    reference_csv: Optional[str] = None

    def to_scenario_dict(self, random_seed: int = 42) -> Dict[str, Any]:
        """Converts definition into the standard scenario JSON structure."""
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
                "initial_x": None,
                "initial_y": None,
            },
            "target": {
                "count": 1,
                "size": self.target_size,
                "shape": self.target_shape,
                "intensity": self.target_intensity,
                "initial_position": "center",
                "initial_x": 1000.0,
                "initial_y": 1000.0,
                "speed": self.target_speed,
            },
            "motion": {
                "motion_type": self.motion_type,
                "circle_radius": self.motion_params.get("circle_radius", 200.0),
                "figure8_radius_x": self.motion_params.get("figure8_radius_x", 250.0),
                "figure8_radius_y": self.motion_params.get("figure8_radius_y", 150.0),
                "random_max_displacement": self.motion_params.get("random_max_displacement", 10.0),
                "straight_line_angle_deg": self.motion_params.get("straight_line_angle_deg", 45.0),
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
                "random_seed": random_seed,
                "mode": self.source_type,
                "mp4_path": self.mp4_path,
            },
            "logging": {
                "csv_enabled": False,
                "json_summary_enabled": False,
                "output_dir": "output",
            },
        }


class StandardBenchmarkMatrix:
    """
    Standard Benchmark Matrix per SIH Problem Statement 26169.
    Maintains the 19 standard scenario definitions.
    """

    # Category 1: Motion Sub-matrix
    SCENARIO_LINEAR = BenchmarkScenarioDefinition(
        scenario_id="matrix_01_linear_nominal",
        name="Nominal Linear Motion",
        category="MOTION",
        description="Linear straight-line trajectory across the optical boresight at nominal speed (50 px/s).",
        motion_type="STRAIGHT_LINE",
        target_speed=50.0,
        motion_params={"straight_line_angle_deg": 35.0},
        default_frames=60,
    )
    SCENARIO_CIRCULAR = BenchmarkScenarioDefinition(
        scenario_id="matrix_02_circular_nominal",
        name="Nominal Circular Orbit",
        category="MOTION",
        description="Circular orbit trajectory around boresight (radius 200 px) at nominal speed (50 px/s).",
        motion_type="CIRCULAR",
        target_speed=50.0,
        motion_params={"circle_radius": 200.0},
        default_frames=60,
    )
    SCENARIO_FIGURE8 = BenchmarkScenarioDefinition(
        scenario_id="matrix_03_figure8_nominal",
        name="Nominal Figure-8 Trajectory",
        category="MOTION",
        description="Figure-8 motion pattern testing bidirectional acceleration and curvature reversals.",
        motion_type="FIGURE_8",
        target_speed=55.0,
        motion_params={"figure8_radius_x": 250.0, "figure8_radius_y": 140.0},
        default_frames=60,
    )
    SCENARIO_RANDOM = BenchmarkScenarioDefinition(
        scenario_id="matrix_04_random_walk",
        name="Stochastic Random Walk",
        category="MOTION",
        description="Stochastic random walk trajectory with continuous velocity drift.",
        motion_type="RANDOM",
        target_speed=45.0,
        motion_params={"random_max_displacement": 12.0},
        default_frames=60,
    )

    # Category 2: Kinematic & Scale Stress
    SCENARIO_HIGH_SPEED = BenchmarkScenarioDefinition(
        scenario_id="matrix_05_high_speed",
        name="High-Speed Linear Crossing",
        category="KINEMATICS",
        description="Rapid target crossing at 80 px/s stressing tracker velocity prediction and Kalman filtering.",
        motion_type="STRAIGHT_LINE",
        target_speed=80.0,
        motion_params={"straight_line_angle_deg": 50.0},
        default_frames=60,
    )
    SCENARIO_SMALL_TARGET = BenchmarkScenarioDefinition(
        scenario_id="matrix_06_small_dim_beacon",
        name="Small & Dim Beacon Spot",
        category="KINEMATICS",
        description="Sub-aperture small spot (size 6 px, intensity 120) stressing detection SNR and subpixel localization.",
        motion_type="CIRCULAR",
        target_size=6,
        target_intensity=120,
        target_speed=45.0,
        motion_params={"circle_radius": 180.0},
        default_frames=60,
    )
    SCENARIO_LARGE_TARGET = BenchmarkScenarioDefinition(
        scenario_id="matrix_07_large_saturated_beacon",
        name="Large Saturated Beacon Spot",
        category="KINEMATICS",
        description="Large saturated spot (size 16 px, intensity 255) testing centroid annulus weighting against saturation.",
        motion_type="CIRCULAR",
        target_size=16,
        target_intensity=255,
        target_speed=45.0,
        motion_params={"circle_radius": 180.0},
        default_frames=60,
    )

    # Category 3: Atmospheric Degradation
    SCENARIO_ATMOS_HAZE = BenchmarkScenarioDefinition(
        scenario_id="matrix_08_atmos_haze",
        name="Atmospheric Haze Degradation",
        category="ATMOSPHERIC",
        description="Moderate atmospheric haze reducing local contrast to 60% with background illumination shift.",
        motion_type="CIRCULAR",
        atmospheric_condition="HAZE",
        atmos_params={"contrast_factor": 0.6, "brightness_offset": 25},
        target_speed=50.0,
        motion_params={"circle_radius": 200.0},
        default_frames=60,
    )
    SCENARIO_ATMOS_FOG = BenchmarkScenarioDefinition(
        scenario_id="matrix_09_atmos_fog",
        name="Severe Atmospheric Fog",
        category="ATMOSPHERIC",
        description="Dense fog severely reducing optical contrast to 35% with +50 brightness offset.",
        motion_type="CIRCULAR",
        atmospheric_condition="FOG",
        atmos_params={"contrast_factor": 0.35, "brightness_offset": 50},
        target_speed=45.0,
        motion_params={"circle_radius": 190.0},
        default_frames=60,
    )
    SCENARIO_ATMOS_RAIN = BenchmarkScenarioDefinition(
        scenario_id="matrix_10_atmos_rain",
        name="Precipitation / Rain Degradation",
        category="ATMOSPHERIC",
        description="Atmospheric rain attenuation reducing optical transmission.",
        motion_type="STRAIGHT_LINE",
        atmospheric_condition="RAIN",
        atmos_params={"contrast_factor": 0.7, "brightness_offset": 15},
        target_speed=50.0,
        motion_params={"straight_line_angle_deg": 30.0},
        default_frames=60,
    )
    SCENARIO_ATMOS_LOW_LIGHT = BenchmarkScenarioDefinition(
        scenario_id="matrix_11_atmos_low_light",
        name="Low-Light Night Operation",
        category="ATMOSPHERIC",
        description="Low ambient background with attenuated spot contrast.",
        motion_type="STRAIGHT_LINE",
        atmospheric_condition="LOW_LIGHT",
        atmos_params={"contrast_factor": 0.45, "brightness_offset": -30},
        target_speed=50.0,
        motion_params={"straight_line_angle_deg": 40.0},
        default_frames=60,
    )

    # Category 4: Sensor Noise
    SCENARIO_NOISE_GAUSSIAN = BenchmarkScenarioDefinition(
        scenario_id="matrix_12_noise_gaussian",
        name="Additive Gaussian Sensor Noise",
        category="NOISE",
        description="Additive thermal/sensor read noise with sigma=12.0 testing candidate thresholding.",
        motion_type="CIRCULAR",
        noise_gaussian_enabled=True,
        noise_gaussian_sigma=12.0,
        target_speed=50.0,
        motion_params={"circle_radius": 200.0},
        default_frames=60,
    )
    SCENARIO_NOISE_SP = BenchmarkScenarioDefinition(
        scenario_id="matrix_13_noise_salt_and_pepper",
        name="Impulse Salt & Pepper Noise",
        category="NOISE",
        description="High-density impulse defect noise (8% density) testing median filtering and outlier rejection.",
        motion_type="FIGURE_8",
        noise_sp_enabled=True,
        noise_sp_density=0.08,
        target_speed=50.0,
        motion_params={"figure8_radius_x": 220.0, "figure8_radius_y": 130.0},
        default_frames=60,
    )
    SCENARIO_NOISE_POISSON = BenchmarkScenarioDefinition(
        scenario_id="matrix_14_noise_poisson",
        name="Poisson Shot Noise",
        category="NOISE",
        description="Signal-dependent quantum shot noise reflecting photon arrival statistics.",
        motion_type="STRAIGHT_LINE",
        noise_poisson_enabled=True,
        target_speed=50.0,
        motion_params={"straight_line_angle_deg": 35.0},
        default_frames=60,
    )

    # Category 5: Geometric Disturbances
    SCENARIO_JITTER_MILD = BenchmarkScenarioDefinition(
        scenario_id="matrix_15_jitter_mild",
        name="Mild Camera Jitter",
        category="GEOMETRIC",
        description="High-frequency mechanical jitter (max 3.0 px/frame) testing Kalman temporal smoothing.",
        motion_type="CIRCULAR",
        jitter_enabled=True,
        jitter_max_px=3.0,
        target_speed=50.0,
        motion_params={"circle_radius": 200.0},
        default_frames=60,
    )
    SCENARIO_JITTER_SEVERE = BenchmarkScenarioDefinition(
        scenario_id="matrix_16_jitter_severe",
        name="Severe Camera Jitter",
        category="GEOMETRIC",
        description="High-amplitude mechanical vibration (max 6.0 px/frame) near PS operational envelope.",
        motion_type="CIRCULAR",
        jitter_enabled=True,
        jitter_max_px=6.0,
        target_speed=50.0,
        motion_params={"circle_radius": 200.0},
        default_frames=60,
    )
    SCENARIO_PLATFORM_LINEAR = BenchmarkScenarioDefinition(
        scenario_id="matrix_17_platform_linear_drift",
        name="Linear Platform Motion Drift",
        category="GEOMETRIC",
        description="Sinusoidal platform attitude drift (max 5.0 px/frame) simulating naval/aerial vehicle motion.",
        motion_type="FIGURE_8",
        platform_motion_enabled=True,
        platform_motion_type="LINEAR",
        platform_motion_max_px=5.0,
        target_speed=50.0,
        motion_params={"figure8_radius_x": 220.0, "figure8_radius_y": 130.0},
        default_frames=60,
    )

    # Category 6: Combined FSOC Stress Scenarios
    SCENARIO_COMBINED_FOG_NOISE_JITTER = BenchmarkScenarioDefinition(
        scenario_id="matrix_18_combined_fog_noise_jitter",
        name="Combined Fog + Gaussian Noise + Jitter",
        category="COMBINED",
        description="Multi-hazard FSOC environment: Atmospheric Fog + Gaussian Noise (sigma=10.0) + Camera Jitter (3.0 px).",
        motion_type="CIRCULAR",
        atmospheric_condition="FOG",
        atmos_params={"contrast_factor": 0.45, "brightness_offset": 40},
        noise_gaussian_enabled=True,
        noise_gaussian_sigma=10.0,
        jitter_enabled=True,
        jitter_max_px=3.0,
        target_speed=50.0,
        motion_params={"circle_radius": 200.0},
        default_frames=60,
    )
    SCENARIO_COMBINED_TURBULENCE = BenchmarkScenarioDefinition(
        scenario_id="matrix_19_combined_turbulence_platform",
        name="Combined Haze + S&P Noise + Platform Motion",
        category="COMBINED",
        description="Hostile field environment: Atmospheric Haze + 5% Salt & Pepper + Linear Platform Drift (4.0 px).",
        motion_type="FIGURE_8",
        atmospheric_condition="HAZE",
        atmos_params={"contrast_factor": 0.55, "brightness_offset": 20},
        noise_sp_enabled=True,
        noise_sp_density=0.05,
        platform_motion_enabled=True,
        platform_motion_type="LINEAR",
        platform_motion_max_px=4.0,
        target_speed=50.0,
        motion_params={"figure8_radius_x": 220.0, "figure8_radius_y": 130.0},
        default_frames=60,
    )

    @classmethod
    def get_all_scenarios(cls) -> List[BenchmarkScenarioDefinition]:
        """Returns all 19 defined standard scenarios."""
        return [
            cls.SCENARIO_LINEAR,
            cls.SCENARIO_CIRCULAR,
            cls.SCENARIO_FIGURE8,
            cls.SCENARIO_RANDOM,
            cls.SCENARIO_HIGH_SPEED,
            cls.SCENARIO_SMALL_TARGET,
            cls.SCENARIO_LARGE_TARGET,
            cls.SCENARIO_ATMOS_HAZE,
            cls.SCENARIO_ATMOS_FOG,
            cls.SCENARIO_ATMOS_RAIN,
            cls.SCENARIO_ATMOS_LOW_LIGHT,
            cls.SCENARIO_NOISE_GAUSSIAN,
            cls.SCENARIO_NOISE_SP,
            cls.SCENARIO_NOISE_POISSON,
            cls.SCENARIO_JITTER_MILD,
            cls.SCENARIO_JITTER_SEVERE,
            cls.SCENARIO_PLATFORM_LINEAR,
            cls.SCENARIO_COMBINED_FOG_NOISE_JITTER,
            cls.SCENARIO_COMBINED_TURBULENCE,
        ]

    @classmethod
    def get_scenarios(cls, subset: BenchmarkSubset | str) -> List[BenchmarkScenarioDefinition]:
        """
        Filters and returns the scenario definitions corresponding to the requested subset.
        """
        if isinstance(subset, str):
            subset = BenchmarkSubset(subset.upper())

        all_scenarios = cls.get_all_scenarios()

        if subset == BenchmarkSubset.FULL:
            return all_scenarios

        if subset == BenchmarkSubset.SMOKE:
            # 3 fast sanity check scenarios: clean linear, circular, and fog disturbance
            return [
                cls.SCENARIO_LINEAR,
                cls.SCENARIO_CIRCULAR,
                cls.SCENARIO_ATMOS_FOG,
            ]

        if subset == BenchmarkSubset.CORE:
            # 6 primary SIH PS validation scenarios
            return [
                cls.SCENARIO_LINEAR,
                cls.SCENARIO_CIRCULAR,
                cls.SCENARIO_FIGURE8,
                cls.SCENARIO_RANDOM,
                cls.SCENARIO_ATMOS_FOG,
                cls.SCENARIO_JITTER_MILD,
            ]

        if subset == BenchmarkSubset.DISTURBANCE:
            # 8 focused disturbance tests
            return [
                cls.SCENARIO_ATMOS_HAZE,
                cls.SCENARIO_ATMOS_FOG,
                cls.SCENARIO_ATMOS_LOW_LIGHT,
                cls.SCENARIO_NOISE_GAUSSIAN,
                cls.SCENARIO_NOISE_SP,
                cls.SCENARIO_JITTER_MILD,
                cls.SCENARIO_PLATFORM_LINEAR,
                cls.SCENARIO_COMBINED_FOG_NOISE_JITTER,
            ]

        return all_scenarios


@dataclass
class BenchmarkMatrixResults:
    """
    Container for the aggregated outputs of a benchmark matrix execution.
    """
    suite_id: str
    subset: BenchmarkSubset
    random_seed: int
    algorithms_tested: List[str]
    scenarios_executed: List[str]
    run_results: List[EvaluationRunResult]
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    crashed_runs: int = 0
    invalid_runs: int = 0
    total_frames_processed: int = 0
    overall_duration_s: float = 0.0
    mean_algorithm_fps: float = 0.0
    mean_benchmark_fps: float = 0.0
    mean_rmse_centroid: Optional[float] = None
    mean_acquisition_time_s: Optional[float] = None
    mean_target_loss_rate: float = 0.0
    passed_sih_spec: bool = False
    timestamp: float = field(default_factory=time.time)

    @property
    def batch_id(self) -> str:
        """Backward-compatibility alias for suite_id."""
        return self.suite_id

    @property
    def passed_fps_spec(self) -> bool:
        """Backward-compatibility property checking if mean FPS meets minimum spec."""
        return self.mean_algorithm_fps >= 20.0

    @property
    def mean_target_loss_rate_pct(self) -> float:
        """Backward-compatibility property returning loss rate as percentage."""
        return self.mean_target_loss_rate * 100.0

    @property
    def run_items(self) -> List[EvaluationRunResult]:
        """Backward-compatibility alias for run_results."""
        return self.run_results


    def to_dict(self) -> Dict[str, Any]:
        """Converts results into a JSON-serializable dictionary."""
        return {
            "suite_id": self.suite_id,
            "subset": self.subset.value,
            "random_seed": self.random_seed,
            "algorithms_tested": self.algorithms_tested,
            "scenarios_executed": self.scenarios_executed,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "crashed_runs": self.crashed_runs,
            "invalid_runs": self.invalid_runs,
            "total_frames_processed": self.total_frames_processed,
            "overall_duration_s": self.overall_duration_s,
            "mean_algorithm_fps": self.mean_algorithm_fps,
            "mean_benchmark_fps": self.mean_benchmark_fps,
            "mean_rmse_centroid": self.mean_rmse_centroid,
            "mean_acquisition_time_s": self.mean_acquisition_time_s,
            "mean_target_loss_rate": self.mean_target_loss_rate,
            "passed_sih_spec": self.passed_sih_spec,
            "timestamp": self.timestamp,
            "runs": [r.to_dict() for r in self.run_results],
        }


class BenchmarkMatrixRunner:
    """
    Orchestrates the deterministic execution of the Standard Benchmark Matrix.
    Uses EvaluationHarness to execute individual isolated scenario runs.
    """

    def __init__(self, harness: EvaluationHarness) -> None:
        self.harness = harness

    def run_matrix(
        self,
        subset: BenchmarkSubset | str = BenchmarkSubset.CORE,
        algorithms: Optional[List[str]] = None,
        random_seed: int = 42,
        max_frames_override: Optional[int] = None,
        output_dir: Optional[str] = None,
        plugins_dir: Optional[str] = None,
    ) -> BenchmarkMatrixResults:
        """
        Executes the specified benchmark matrix subset across all target algorithms.

        Args:
            subset: The matrix subset to execute (SMOKE, CORE, DISTURBANCE, FULL).
            algorithms: List of algorithm plugin IDs to evaluate. Default: active algorithm or ['baseline_tracker'].
            random_seed: Deterministic seed for repeatable frame generation.
            max_frames_override: Optional override for frame count per scenario.
            output_dir: Output directory for reports and telemetry.
            plugins_dir: Optional custom plugins directory override.

        Returns:
            BenchmarkMatrixResults with comprehensive outcomes.
        """
        from src.evaluation.harness import EvaluationExperiment, EvaluationOutcome

        if isinstance(subset, str):
            subset = BenchmarkSubset(subset.upper())

        target_out_dir = output_dir or os.path.join("output", "matrix")
        os.makedirs(target_out_dir, exist_ok=True)

        # 1. Resolve algorithms
        if not algorithms:
            app = self.harness.app
            if app and hasattr(app, "active_algorithm_name") and app.active_algorithm_name:
                algorithms = [app.active_algorithm_name]
            else:
                algorithms = ["baseline_tracker"]

        scenarios = StandardBenchmarkMatrix.get_scenarios(subset)
        suite_id = f"matrix_{subset.value.lower()}_{int(time.time())}"

        logger.info(
            f"Starting Benchmark Matrix execution: Suite='{suite_id}', "
            f"Subset='{subset.value}', Scenarios={len(scenarios)}, "
            f"Algorithms={algorithms}, Seed={random_seed}"
        )

        all_results: List[EvaluationRunResult] = []
        t0 = time.perf_counter()

        # Temporary directory for scenario JSON specifications
        temp_scenario_dir = os.path.join(target_out_dir, "scenarios")
        os.makedirs(temp_scenario_dir, exist_ok=True)

        for s_def in scenarios:
            # Materialize deterministic scenario JSON
            scenario_json_path = os.path.join(temp_scenario_dir, f"{s_def.scenario_id}.json")
            with open(scenario_json_path, "w", encoding="utf-8") as f:
                json.dump(s_def.to_scenario_dict(random_seed=random_seed), f, indent=2)

            frames_to_run = max_frames_override or s_def.default_frames

            for algo_id in algorithms:
                exp_id = f"{suite_id}_{s_def.scenario_id}_{algo_id}"
                experiment = EvaluationExperiment(
                    experiment_id=exp_id,
                    algorithm_name=algo_id,
                    source_type=s_def.source_type,
                    scenario_path=scenario_json_path if s_def.source_type == "SIMULATION" else None,
                    mp4_path=s_def.mp4_path,
                    reference_csv=s_def.reference_csv,
                    random_seed=random_seed,
                    max_frames=frames_to_run,
                    output_dir=os.path.join(target_out_dir, s_def.scenario_id),
                    plugins_dir=plugins_dir,
                )

                logger.info(f"Running scenario '{s_def.scenario_id}' with algorithm '{algo_id}'...")
                res = self.harness.run_experiment(experiment)
                all_results.append(res)


        overall_duration = time.perf_counter() - t0

        # Aggregate metrics
        successful = [r for r in all_results if r.outcome == EvaluationOutcome.SUCCESS]
        failed = [r for r in all_results if r.outcome == EvaluationOutcome.FAILED]
        crashed = [r for r in all_results if r.outcome == EvaluationOutcome.CRASHED]
        invalid = [r for r in all_results if r.outcome == EvaluationOutcome.INVALID]

        total_frames = sum(r.total_frames for r in all_results)
        mean_algo_fps = (
            sum(r.algorithm_fps for r in successful) / len(successful)
            if successful else 0.0
        )
        mean_bench_fps = (
            sum(r.benchmark_fps for r in successful) / len(successful)
            if successful else 0.0
        )

        rmse_vals = [r.centroid_rmse for r in successful if r.centroid_rmse is not None]
        mean_rmse = (sum(rmse_vals) / len(rmse_vals)) if rmse_vals else None

        acq_vals = [r.acquisition_time_s for r in successful if r.acquisition_time_s is not None]
        mean_acq = (sum(acq_vals) / len(acq_vals)) if acq_vals else None

        mean_loss = (
            sum(r.target_loss_rate for r in successful) / len(successful)
            if successful else 0.0
        )

        # SIH PS 26169 Threshold Verification
        passed_fps = mean_algo_fps >= 20.0 and len(successful) > 0
        passed_acq = (mean_acq is None or mean_acq <= 2.0) and len(successful) > 0
        passed_err = (mean_rmse is None or mean_rmse <= 10.0) and len(successful) > 0
        passed_loss = mean_loss < 5.0 and len(successful) > 0
        passed_sih = (
            passed_fps
            and passed_acq
            and passed_err
            and passed_loss
            and len(failed) == 0
            and len(crashed) == 0
            and len(invalid) == 0
            and len(successful) > 0
        )

        matrix_results = BenchmarkMatrixResults(
            suite_id=suite_id,
            subset=subset,
            random_seed=random_seed,
            algorithms_tested=algorithms,
            scenarios_executed=[s.scenario_id for s in scenarios],
            run_results=all_results,
            total_runs=len(all_results),
            successful_runs=len(successful),
            failed_runs=len(failed),
            crashed_runs=len(crashed),
            invalid_runs=len(invalid),
            total_frames_processed=total_frames,
            overall_duration_s=overall_duration,
            mean_algorithm_fps=mean_algo_fps,
            mean_benchmark_fps=mean_bench_fps,
            mean_rmse_centroid=mean_rmse,
            mean_acquisition_time_s=mean_acq,
            mean_target_loss_rate=mean_loss,
            passed_sih_spec=passed_sih,
        )

        import shutil
        # Cleanup temp scenarios if they exist
        if os.path.exists(temp_scenario_dir):
            shutil.rmtree(temp_scenario_dir, ignore_errors=True)
            
        # Cleanup empty scenario output directories
        for s_def in scenarios:
            s_dir = os.path.join(target_out_dir, s_def.scenario_id)
            if os.path.exists(s_dir) and not os.listdir(s_dir):
                os.rmdir(s_dir)

        return matrix_results
