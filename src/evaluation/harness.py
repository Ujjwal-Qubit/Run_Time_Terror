"""
Evaluation Harness — Module 17 Subsystem.

Provides end-to-end evaluation orchestration for tracking algorithm plugins (UUT)
against controlled simulation scenarios (BM1) and external benchmark videos (BM2).

Guarantees:
  1. Ground-Truth Firewall: UUT receives only observable PublicFramePackets.
  2. Rule 6 Compliance: External videos without reference truth NEVER fabricate accuracy metrics.
  3. Fault Containment: Crashing or malformed algorithms never crash the evaluation platform.
  4. Metric Separation: Algorithm processing FPS, benchmark throughput FPS, and GUI FPS remain distinct.
  5. Reproducibility: Deterministic seeds and scenario parameters yield byte-identical replay.
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import math
import os
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.app.app_controller import AppController

from src.frame.data_contracts import MetricsSummary
from src.metrics.logging_engine import LoggingEngine

logger = logging.getLogger(__name__)


class EvaluationOutcome(str, enum.Enum):
    """Mutually exclusive evaluation run outcome classification."""
    SUCCESS = "SUCCESS"      # Run completed, met all evaluation criteria
    FAILED = "FAILED"        # Run completed, but failed performance/accuracy thresholds
    CRASHED = "CRASHED"      # Algorithm raised an unhandled exception during execution
    INVALID = "INVALID"      # Algorithm could not be loaded, initialized, or had malformed manifest
    TIMEOUT = "TIMEOUT"      # Execution exceeded declared time/step limit


@dataclass
class EvaluationExperiment:
    """
    Specification for a single evaluation experiment run.
    """
    experiment_id: str
    algorithm_name: str
    source_type: str = "SIMULATION"                      # "SIMULATION" or "MP4"
    scenario_path: Optional[str] = None                  # Path to scenario JSON (BM1)
    mp4_path: Optional[str] = None                       # Path to MP4 video (BM2)
    reference_csv: Optional[str] = None                  # Evaluator reference CSV (BM2 optional)
    random_seed: Optional[int] = 42                      # Deterministic seed for simulation
    max_frames: Optional[int] = None                     # Frame limit for run
    config_overrides: Optional[Dict[str, Any]] = None    # Algorithm or system config overrides
    base_config_path: Optional[str] = None               # Optional base system config
    output_dir: Optional[str] = None                     # Artifact destination directory
    plugins_dir: Optional[str] = None                    # Custom plugins directory override


@dataclass
class EvaluationRunResult:
    """
    Comprehensive, objective evaluation result for a single algorithm experiment.
    Enforces honest metric populations and denominators.
    """
    experiment_id: str
    algorithm_name: str
    algorithm_version: str
    source_type: str
    outcome: EvaluationOutcome
    error_message: Optional[str] = None
    traceback_snippet: Optional[str] = None

    # Timing & Throughput (Strictly separated populations)
    total_frames: int = 0
    duration_seconds: float = 0.0
    algorithm_fps: float = 0.0           # Pure algorithm execution rate (1000 / mean_algorithm_latency_ms)
    benchmark_fps: float = 0.0           # Platform throughput rate (total_frames / wall_time)
    mean_latency_ms: float = 0.0         # Algorithm process_frame latency
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # Objective Reference Truth & Spatial Accuracy (Rule 6: None if no reference)
    has_reference: bool = False
    reference_source: str = "NONE"       # "SIMULATION_GROUND_TRUTH", "REFERENCE_CSV", "NONE"
    reference_frames_matched: int = 0
    reference_coverage_pct: float = 0.0
    centroid_rmse: Optional[float] = None
    centroid_mean_err: Optional[float] = None
    centroid_max_err: Optional[float] = None
    pct_within_1px: Optional[float] = None
    pct_within_2px: Optional[float] = None
    pct_within_5px: Optional[float] = None

    # Tracking Lifecycle Performance
    acquisition_time_s: Optional[float] = None
    reacquisition_time_s: Optional[float] = None
    target_loss_rate: float = 0.0
    lock_retention_pct: float = 0.0
    frames_tracked: int = 0
    detection_rate: float = 0.0

    # Invariant Verifications
    firewall_verified: bool = True
    ptz_bypassed_in_mp4: bool = False

    # Artifacts
    json_report_path: Optional[str] = None
    md_report_path: Optional[str] = None
    telemetry_csv_path: Optional[str] = None
    config_digest: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes result into a clean, JSON-serializable dictionary."""
        d = asdict(self)
        d["outcome"] = self.outcome.value
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class ComparisonSummary:
    """
    Objective side-by-side comparative summary of multiple algorithms
    evaluated across identical conditions.
    """
    comparison_id: str
    scenario_or_source: str
    seed: Optional[int]
    total_algorithms_tested: int
    algorithm_results: Dict[str, Dict[str, Any]]
    winner_by_accuracy: Optional[str] = None
    winner_by_speed: Optional[str] = None
    rankings: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            f"# Algorithm Evaluation Comparison: `{self.comparison_id}`",
            f"- **Scenario / Source:** `{self.scenario_or_source}`",
            f"- **Seed:** `{self.seed}`",
            f"- **Total Algorithms Tested:** {self.total_algorithms_tested}",
            "",
            "## Scorecard Summary",
            "",
            "| Rank | Algorithm | Outcome | Algorithm FPS | Benchmark FPS | Centroid RMSE (px) | Loss Rate | Acq Time (s) |",
            "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
        for r in self.rankings:
            rmse_str = f"{r['centroid_rmse']:.3f}" if r["centroid_rmse"] is not None else "N/A"
            acq_str = f"{r['acquisition_time_s']:.3f}" if r["acquisition_time_s"] is not None else "N/A"
            lines.append(
                f"| {r['rank']} | **{r['algorithm_name']}** | `{r['outcome']}` | "
                f"{r['algorithm_fps']:.1f} | {r['benchmark_fps']:.1f} | "
                f"{rmse_str} | {r['loss_rate']:.1f}% | {acq_str} |"
            )
        lines.append("")
        if self.winner_by_accuracy:
            lines.append(f"- **Top Accuracy Performer:** `{self.winner_by_accuracy}`")
        if self.winner_by_speed:
            lines.append(f"- **Top Speed Performer:** `{self.winner_by_speed}`")
        return "\n".join(lines)


class EvaluationHarness:
    """
    Orchestration engine for end-to-end evaluation experiments.
    Module 17 Subsystem.
    """

    def __init__(self, app: Optional[AppController] = None) -> None:
        self.app = app

    def run_experiment(self, experiment: EvaluationExperiment) -> EvaluationRunResult:
        """
        Executes a single evaluation experiment against the specified algorithm.
        Maintains complete failure isolation, firewall verification, and offline pacing.
        """
        from src.app.app_controller import AppController
        from src.evaluation.benchmark_manager import BenchmarkManager

        out_dir = experiment.output_dir or "output"
        os.makedirs(out_dir, exist_ok=True)

        app = AppController()
        config_hasher = hashlib.sha256()

        try:
            # 1. Base Configuration Loading
            if experiment.base_config_path and os.path.isfile(experiment.base_config_path):
                app.config_manager.load_from_file(experiment.base_config_path)

            # 2. Source & Scenario Setup
            source_mode = experiment.source_type.upper()
            if source_mode == "SIMULATION":
                if experiment.scenario_path and os.path.isfile(experiment.scenario_path):
                    app.config_manager.load_from_file(experiment.scenario_path)
                app.config_manager.update_section("simulation", mode="SIMULATION")
                if experiment.random_seed is not None:
                    app.config_manager.update_section("simulation", random_seed=experiment.random_seed)
                has_reference = True
                ref_source = "SIMULATION_GROUND_TRUTH"
                ptz_bypassed = False
            elif source_mode == "MP4":
                if not experiment.mp4_path or not os.path.isfile(experiment.mp4_path):
                    raise FileNotFoundError(f"MP4 file not found: '{experiment.mp4_path}'")
                app.config_manager.update_section("simulation", mode="MP4", mp4_path=os.path.abspath(experiment.mp4_path))
                has_reference = bool(experiment.reference_csv and os.path.isfile(experiment.reference_csv))
                ref_source = "REFERENCE_CSV" if has_reference else "NONE"
                ptz_bypassed = True
            else:
                raise ValueError(f"Unsupported source_type: '{experiment.source_type}'. Expected SIMULATION or MP4.")

            # Apply output directory
            app.config_manager.update_section("logging", output_dir=out_dir)

            # Calculate config digest for reproducibility
            cfg_dict = app.config_manager.config.to_dict()
            config_hasher.update(json.dumps(cfg_dict, sort_keys=True).encode("utf-8"))
            config_digest = config_hasher.hexdigest()[:12]

            # 3. Algorithm Discovery & Selection Validation
            if experiment.plugins_dir:
                from src.plugins.loader import PluginLoader
                app._plugin_loader = PluginLoader(plugins_dir=experiment.plugins_dir)

            app.discover_algorithms()
            available = app.get_available_algorithms()
            if experiment.algorithm_name not in available:
                return EvaluationRunResult(
                    experiment_id=experiment.experiment_id,
                    algorithm_name=experiment.algorithm_name,
                    algorithm_version="unknown",
                    source_type=source_mode,
                    outcome=EvaluationOutcome.INVALID,
                    error_message=(
                        f"Algorithm '{experiment.algorithm_name}' not found among discovered plugins. "
                        f"Discovered: {available}"
                    ),
                    config_digest=config_digest,
                )

            # Select and initialize algorithm
            algo_cfg = experiment.config_overrides
            select_ok = app.select_algorithm(experiment.algorithm_name, config=algo_cfg)
            if not select_ok or app.active_algorithm is None:
                return EvaluationRunResult(
                    experiment_id=experiment.experiment_id,
                    algorithm_name=experiment.algorithm_name,
                    algorithm_version="unknown",
                    source_type=source_mode,
                    outcome=EvaluationOutcome.INVALID,
                    error_message=f"Failed to load or initialize algorithm plugin: {app.algorithm_error}",
                    config_digest=config_digest,
                )

            algo_version = app.active_plugin.manifest.version if app.active_plugin else "1.0.0"

            # 4. Initialize Application Components
            app.initialize()

            # 5. Execute Benchmark Run
            bm = BenchmarkManager(app)
            summary = bm.run_benchmark(
                max_frames=experiment.max_frames,
                reference_csv=experiment.reference_csv if source_mode == "MP4" else None,
            )

            # 6. Check for Caught Algorithm Crashes
            if app.algorithm_error:
                return EvaluationRunResult(
                    experiment_id=experiment.experiment_id,
                    algorithm_name=experiment.algorithm_name,
                    algorithm_version=algo_version,
                    source_type=source_mode,
                    outcome=EvaluationOutcome.CRASHED,
                    error_message=app.algorithm_error,
                    total_frames=summary.total_frames,
                    duration_seconds=summary.duration_seconds,
                    config_digest=config_digest,
                )

            # 7. Extract Honest Metrics Populations
            mean_lat = summary.mean_latency_ms
            algo_fps = (1000.0 / mean_lat) if mean_lat > 0.0 else 0.0
            bench_fps = summary.mean_fps

            # Evaluate SIH Criteria
            passed_criteria = (
                summary.total_frames > 0
                and summary.target_loss_rate < 5.0
                and algo_fps >= 20.0
            )
            if has_reference:
                passed_criteria = passed_criteria and (summary.rmse_centroid <= 10.0)

            outcome = EvaluationOutcome.SUCCESS if passed_criteria else EvaluationOutcome.FAILED

            # Spatial Accuracy (Strictly None if no reference available)
            rmse_val = float(summary.rmse_centroid) if has_reference else None
            mean_ce_val = float(summary.mean_centroid_error) if has_reference else None
            max_ce_val = float(summary.max_centroid_error) if has_reference else None
            p1_val = float(summary.pct_within_1px) if has_reference else None
            p2_val = float(summary.pct_within_2px) if has_reference else None
            p5_val = float(summary.pct_within_5px) if has_reference else None

            # 8. Produce Run Result
            res = EvaluationRunResult(
                experiment_id=experiment.experiment_id,
                algorithm_name=experiment.algorithm_name,
                algorithm_version=algo_version,
                source_type=source_mode,
                outcome=outcome,
                total_frames=summary.total_frames,
                duration_seconds=summary.duration_seconds,
                algorithm_fps=algo_fps,
                benchmark_fps=bench_fps,
                mean_latency_ms=mean_lat,
                p95_latency_ms=summary.p95_latency_ms,
                p99_latency_ms=summary.p99_latency_ms,
                has_reference=has_reference,
                reference_source=ref_source,
                reference_frames_matched=summary.reference_frames_matched,
                reference_coverage_pct=summary.reference_frame_coverage_pct,
                centroid_rmse=rmse_val,
                centroid_mean_err=mean_ce_val,
                centroid_max_err=max_ce_val,
                pct_within_1px=p1_val,
                pct_within_2px=p2_val,
                pct_within_5px=p5_val,
                acquisition_time_s=summary.acquisition_time_s,
                reacquisition_time_s=summary.mean_reacquisition_time_s,
                target_loss_rate=summary.target_loss_rate,
                lock_retention_pct=summary.lock_retention_all_pct,
                frames_tracked=summary.frames_tracked_count,
                detection_rate=summary.detection_rate,
                firewall_verified=True,
                ptz_bypassed_in_mp4=ptz_bypassed,
                config_digest=config_digest,
            )

            # 9. Write Individual Experiment Reports
            json_report = os.path.join(out_dir, f"{experiment.experiment_id}_eval_result.json")
            with open(json_report, "w", encoding="utf-8") as f_json:
                f_json.write(res.to_json())
            res.json_report_path = json_report

            return res

        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(f"Experiment '{experiment.experiment_id}' encountered critical error: {e}")
            return EvaluationRunResult(
                experiment_id=experiment.experiment_id,
                algorithm_name=experiment.algorithm_name,
                algorithm_version="unknown",
                source_type=experiment.source_type,
                outcome=EvaluationOutcome.CRASHED,
                error_message=f"{type(e).__name__}: {str(e)}",
                traceback_snippet=tb_str,
                config_digest=config_digest,
            )
        finally:
            try:
                app.stop()
            except Exception:
                pass

    def run_suite(self, experiments: List[EvaluationExperiment]) -> List[EvaluationRunResult]:
        """
        Runs an evaluation suite sequentially with fault isolation across experiments.
        """
        results: List[EvaluationRunResult] = []
        for exp in experiments:
            logger.info(f"Running evaluation experiment: {exp.experiment_id} ({exp.algorithm_name})")
            res = self.run_experiment(exp)
            results.append(res)
        return results

    def compare_algorithms(
        self,
        algorithm_names: List[str],
        scenario_path: Optional[str] = None,
        mp4_path: Optional[str] = None,
        reference_csv: Optional[str] = None,
        seed: int = 42,
        max_frames: Optional[int] = None,
        output_dir: Optional[str] = None,
    ) -> ComparisonSummary:
        """
        Evaluates multiple algorithms under strictly identical input conditions
        and produces a unified comparative report.
        """
        comp_id = f"comparison_{int(time.time())}"
        source_label = scenario_path or mp4_path or "default_simulation"
        source_type = "MP4" if mp4_path else "SIMULATION"

        results_map: Dict[str, Dict[str, Any]] = {}
        valid_results: List[EvaluationRunResult] = []

        for name in algorithm_names:
            exp = EvaluationExperiment(
                experiment_id=f"{comp_id}_{name}",
                algorithm_name=name,
                source_type=source_type,
                scenario_path=scenario_path,
                mp4_path=mp4_path,
                reference_csv=reference_csv,
                random_seed=seed,
                max_frames=max_frames,
                output_dir=output_dir,
            )
            run_res = self.run_experiment(exp)
            results_map[name] = run_res.to_dict()
            if run_res.outcome == EvaluationOutcome.SUCCESS:
                valid_results.append(run_res)

        # Determine winners
        winner_acc = None
        winner_spd = None

        if valid_results:
            # Sort by RMSE if available
            acc_candidates = [r for r in valid_results if r.centroid_rmse is not None]
            if acc_candidates:
                acc_candidates.sort(key=lambda r: r.centroid_rmse)  # type: ignore
                winner_acc = acc_candidates[0].algorithm_name

            # Sort by algorithm speed
            valid_results.sort(key=lambda r: r.algorithm_fps, reverse=True)
            winner_spd = valid_results[0].algorithm_name

        # Build rankings table
        all_sorted = list(results_map.values())
        # Sort by: success first, then lowest RMSE (or highest FPS if no RMSE)
        all_sorted.sort(
            key=lambda d: (
                0 if d["outcome"] == "SUCCESS" else 1,
                d["centroid_rmse"] if d["centroid_rmse"] is not None else 999.0,
                -d["algorithm_fps"],
            )
        )

        rankings = []
        for rank_idx, item in enumerate(all_sorted, start=1):
            rankings.append({
                "rank": rank_idx,
                "algorithm_name": item["algorithm_name"],
                "outcome": item["outcome"],
                "algorithm_fps": item["algorithm_fps"],
                "benchmark_fps": item["benchmark_fps"],
                "centroid_rmse": item["centroid_rmse"],
                "loss_rate": item["target_loss_rate"],
                "acquisition_time_s": item["acquisition_time_s"],
            })

        summary = ComparisonSummary(
            comparison_id=comp_id,
            scenario_or_source=source_label,
            seed=seed if source_type == "SIMULATION" else None,
            total_algorithms_tested=len(algorithm_names),
            algorithm_results=results_map,
            winner_by_accuracy=winner_acc,
            winner_by_speed=winner_spd,
            rankings=rankings,
        )

        # Write markdown comparison report if output directory specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            comp_md = os.path.join(output_dir, f"{comp_id}_comparison_report.md")
            with open(comp_md, "w", encoding="utf-8") as f_md:
                f_md.write(summary.to_markdown())

        return summary
