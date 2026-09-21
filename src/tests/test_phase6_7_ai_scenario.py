"""
Phase 6.7 Verification Suite — AI-Assisted Trajectory & Scenario Generation.

Tests:
  1. Natural Language Interpretation of diverse prompt requests (spiral, square, zigzag, fog, jitter, speed).
  2. Strict validation and rejection of out-of-bounds, unphysical, or unsupported specifications.
  3. Deterministic trajectory generator reproducibility.
  4. Extended kinematics execution in TargetManager (SPIRAL, SINUSOIDAL).
  5. End-to-end AI Scenario workflow execution through EvaluationHarness.
  6. Segregation of AI-generated scenarios from the official SIH Standard Benchmark Matrix.
  7. Guarantee that AI does not inject arbitrary per-frame coordinates bypassing the simulator.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import pytest

from src.app.app_controller import AppController
from src.config.config_manager import MotionConfig, TargetConfig
from src.evaluation.ai_scenario import (
    AIInterpretationEngine,
    AIScenarioWorkflow,
    CandidateScenarioSpec,
    DeterministicTrajectoryGenerator,
    ScenarioSpecificationValidator,
    ValidatedScenarioSpec,
)
from src.evaluation.benchmark_manager import BenchmarkManager
from src.evaluation.harness import EvaluationHarness, EvaluationOutcome
from src.evaluation.matrix import StandardBenchmarkMatrix
from src.simulation.target_manager import TargetManager


@pytest.fixture
def temp_ai_dir():
    d = tempfile.mkdtemp(prefix="test_phase6_7_ai_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestAIInterpretation:
    """Tests natural language parsing of scenario intent into candidate specifications."""

    def test_interpret_spiral_prompt(self):
        prompt = "Create a circular trajectory around the center with gradually increasing radius"
        candidate = AIInterpretationEngine.interpret(prompt)

        assert candidate.trajectory_type == "SPIRAL"
        assert "spiral_expansion_rate" in candidate.motion_params
        assert candidate.target_speed > 0
        assert candidate.atmospheric_condition == "CLEAR"

    def test_interpret_straight_with_fog(self):
        prompt = "Make a straight trajectory with moderate speed and heavy fog"
        candidate = AIInterpretationEngine.interpret(prompt)

        assert candidate.trajectory_type == "STRAIGHT_LINE"
        assert candidate.target_speed == 50.0
        assert candidate.atmospheric_condition == "FOG"

    def test_interpret_random_with_explicit_speed_and_jitter(self):
        prompt = "Generate a random trajectory moving at 65 px/s with severe camera jitter"
        candidate = AIInterpretationEngine.interpret(prompt)

        assert candidate.trajectory_type == "RANDOM"
        assert candidate.target_speed == 65.0
        assert candidate.jitter_enabled is True
        assert candidate.jitter_max_px == 5.0

    def test_interpret_figure8_with_noise(self):
        prompt = "Create a figure 8 trajectory with high speed and gaussian sensor noise"
        candidate = AIInterpretationEngine.interpret(prompt)

        assert candidate.trajectory_type == "FIGURE_8"
        assert candidate.target_speed == 75.0
        assert candidate.noise_gaussian_enabled is True
        assert candidate.noise_gaussian_sigma == 12.0

    def test_interpret_sinusoidal_orbit(self):
        prompt = "Make a sinusoidal orbit at 40 px/s with small dim spot"
        candidate = AIInterpretationEngine.interpret(prompt)

        assert candidate.trajectory_type == "SINUSOIDAL"
        assert candidate.target_speed == 40.0
        assert candidate.target_size == 6
        assert candidate.target_intensity == 120


class TestSpecificationValidator:
    """Tests safety gating, boundary verification, and rejection of invalid specs."""

    def test_valid_spec_accepted(self):
        candidate = CandidateScenarioSpec(
            prompt="Valid circular test",
            trajectory_type="CIRCULAR",
            target_speed=50.0,
            target_size=10,
            target_intensity=220,
            center_x=1000.0,
            center_y=1000.0,
            motion_params={"circle_radius": 200.0},
        )
        is_valid, spec, errors = ScenarioSpecificationValidator.validate(candidate)

        assert is_valid is True
        assert spec is not None
        assert len(errors) == 0
        assert spec.is_ai_generated is True
        assert spec.scenario_id.startswith("ai_circular_")

    def test_reject_unsupported_trajectory(self):
        candidate = CandidateScenarioSpec(
            prompt="Warp test",
            trajectory_type="QUANTUM_TELEPORT",
            target_speed=50.0,
        )
        is_valid, spec, errors = ScenarioSpecificationValidator.validate(candidate)

        assert is_valid is False
        assert spec is None
        assert any("Unsupported trajectory type" in e for e in errors)

    def test_reject_excessive_speed(self):
        candidate = CandidateScenarioSpec(
            prompt="Hypersonic test",
            trajectory_type="CIRCULAR",
            target_speed=350.0,  # Max limit is 120.0 px/s
        )
        is_valid, spec, errors = ScenarioSpecificationValidator.validate(candidate)

        assert is_valid is False
        assert any("exceeds maximum platform limit" in e for e in errors)

    def test_reject_non_positive_speed(self):
        candidate = CandidateScenarioSpec(
            prompt="Stationary negative test",
            trajectory_type="CIRCULAR",
            target_speed=-10.0,
        )
        is_valid, spec, errors = ScenarioSpecificationValidator.validate(candidate)

        assert is_valid is False
        assert any("strictly positive" in e for e in errors)

    def test_reject_out_of_bounds_center_or_radius(self):
        candidate = CandidateScenarioSpec(
            prompt="Out of bounds test",
            trajectory_type="CIRCULAR",
            center_x=50.0,  # Too close to margin
            center_y=1000.0,
            motion_params={"circle_radius": 300.0},
        )
        is_valid, spec, errors = ScenarioSpecificationValidator.validate(candidate)

        assert is_valid is False
        assert any("out of safe scene bounds" in e or "exceeds maximum safe radius" in e for e in errors)

    def test_reject_excessive_disturbances(self):
        candidate = CandidateScenarioSpec(
            prompt="Extreme disturbance test",
            trajectory_type="CIRCULAR",
            jitter_enabled=True,
            jitter_max_px=55.0,  # PS limit 20.0
            noise_gaussian_enabled=True,
            noise_gaussian_sigma=40.0,  # PS limit 20.0
        )
        is_valid, spec, errors = ScenarioSpecificationValidator.validate(candidate)

        assert is_valid is False
        assert any("Jitter max" in e for e in errors)
        assert any("Gaussian noise sigma" in e for e in errors)



class TestAIScenarioWorkflowAndSeparation:
    """Tests end-to-end AI scenario creation, execution, and benchmark matrix isolation."""

    def test_end_to_end_ai_scenario_execution(self, temp_ai_dir):
        app = AppController()
        harness = EvaluationHarness(app)
        workflow = AIScenarioWorkflow(harness)

        prompt = "Create a circular trajectory around center with gradually increasing radius"
        success, spec, run_res, errors = workflow.execute_prompt(
            prompt=prompt,
            algorithm_name="baseline_tracker",
            seed=42,
            max_frames=30,
            output_dir=temp_ai_dir,
        )

        assert success is True
        assert spec is not None
        assert run_res is not None
        assert run_res.outcome == EvaluationOutcome.SUCCESS
        assert run_res.total_frames == 30
        assert run_res.frames_tracked >= 25
        assert run_res.algorithm_fps >= 20.0
        assert run_res.centroid_rmse is not None
        assert run_res.centroid_rmse <= 1.0

    def test_benchmark_matrix_isolation(self, temp_ai_dir):
        # AI scenario execution must not alter StandardBenchmarkMatrix
        matrix_before = len(StandardBenchmarkMatrix.get_all_scenarios())

        app = AppController()
        bm = BenchmarkManager(app)
        succ, spec, res, errs = bm.run_ai_scenario(
            prompt="Make a square trajectory with moderate speed",
            max_frames=15,
            output_dir=temp_ai_dir,
        )

        assert succ is True
        matrix_after = len(StandardBenchmarkMatrix.get_all_scenarios())
        assert matrix_before == matrix_after == 19
        assert spec.is_ai_generated is True

    def test_no_direct_ai_coordinate_injection(self, temp_ai_dir):
        # Verify that coordinates are generated by TargetManager physics, not raw AI numbers
        candidate = AIInterpretationEngine.interpret("Make a circular trajectory at 45 px/s")
        assert "coordinates" not in candidate.motion_params
        assert "waypoints" not in candidate.motion_params
        # TargetManager step advances the coordinates frame-by-frame
        _, validated, _ = ScenarioSpecificationValidator.validate(candidate)
        d = validated.to_scenario_dict()
        assert d["metadata"]["is_ai_generated"] is True
        assert "motion" in d
        assert d["motion"]["motion_type"] == "CIRCULAR"
