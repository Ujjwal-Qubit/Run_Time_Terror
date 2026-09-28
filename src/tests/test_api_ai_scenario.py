"""
Regression tests for F-DEF-02: AI Scenario API Response & Tuple Unpacking.

Verifies:
  1. Successful execution of an AI scenario prompt unpacks the 4-tuple and returns
     a conformant schema matching AIScenarioOutcome.
  2. Workflow-level validation failure returns HTTP 200 with valid=False, populated
     validation_errors, and clean empty/null auxiliary structures.
  3. Unexpected internal exceptions are trapped, logged, and return HTTP 500 without
     leaking stack traces, internal paths, or secrets.
  4. Response schema fields (scenario_id, valid, validation_errors, spec, evaluation,
     report_path) are strictly validated.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from src.api.server import run_ai_scenario, AIScenarioRequest
from src.evaluation.ai_scenario import AIScenarioWorkflow, ValidatedScenarioSpec
from src.evaluation.harness import EvaluationOutcome, EvaluationRunResult


def test_ai_scenario_live_nominal_execution():
    """Verify end-to-end execution of a valid prompt against the baseline tracker."""
    req = AIScenarioRequest(
        prompt="Circular target at 50 px/s in clear air",
        algorithm="baseline_tracker",
        seed=42,
        max_frames=5,
    )
    res = run_ai_scenario(req)

    # 1. Verify schema keys
    expected_keys = {"scenario_id", "valid", "validation_errors", "spec", "evaluation", "report_path"}
    assert set(res.keys()) == expected_keys, f"Missing or extra keys in response: {set(res.keys()) ^ expected_keys}"

    # 2. Verify validity and scenario identification
    assert res["valid"] is True, f"Expected valid=True, got errors: {res.get('validation_errors')}"
    assert isinstance(res["scenario_id"], str)
    assert len(res["scenario_id"]) > 0
    assert res["scenario_id"] != "unknown"
    assert res["validation_errors"] == []

    # 3. Verify specification structure
    spec = res["spec"]
    assert isinstance(spec, dict)
    assert "motion" in spec
    assert spec["motion"]["motion_type"] == "CIRCULAR"
    assert "target" in spec
    assert "camera" in spec
    assert "scene" in spec

    # 4. Verify evaluation metrics
    evaluation = res["evaluation"]
    assert evaluation is not None
    assert evaluation["algorithm_fps"] is not None and evaluation["algorithm_fps"] > 0
    assert evaluation["centroid_rmse"] is not None
    assert evaluation["target_loss_rate"] is not None
    assert evaluation["acquisition_time_s"] is not None
    assert isinstance(evaluation["passed_sih_spec"], bool)

    # 5. Verify report path
    report_path = res["report_path"]
    assert isinstance(report_path, str)
    assert report_path.endswith(".json")


def test_ai_scenario_validation_rejection():
    """Verify workflow rejection when a prompt violates kinematic or spatial limits."""
    # Prompt requesting 500 px/s speed which exceeds platform safety limit (120 px/s)
    req = AIScenarioRequest(
        prompt="Circular target moving at 500 px/s in clear air",
        seed=42,
        max_frames=5,
    )
    res = run_ai_scenario(req)

    assert res["valid"] is False
    assert res["scenario_id"] == "unknown"
    assert isinstance(res["validation_errors"], list)
    assert len(res["validation_errors"]) > 0
    assert any("exceeds maximum platform limit" in err for err in res["validation_errors"])
    assert res["spec"] == {}
    assert res["evaluation"] is None
    assert res["report_path"] == ""


def test_ai_scenario_unexpected_internal_exception():
    """Verify that unexpected exceptions return HTTP 500 without leaking secrets or paths."""
    sensitive_path = "C:\\lumitrack\\production\\internal_keys\\secret.key"
    leak_message = f"Disk failure while accessing {sensitive_path}"

    with patch.object(AIScenarioWorkflow, "execute_prompt", side_effect=RuntimeError(leak_message)):
        with pytest.raises(HTTPException) as exc_info:
            run_ai_scenario(AIScenarioRequest(prompt="Circular target at 50 px/s in clear air"))

        assert exc_info.value.status_code == 500
        # Sensitive paths and raw error details must not be exposed to the client
        assert sensitive_path not in exc_info.value.detail
        assert "secret" not in exc_info.value.detail.lower()
        assert "internal error" in exc_info.value.detail.lower()


def test_ai_scenario_mocked_unpacking_and_null_coalescing():
    """Verify that mocked 4-tuple unpacking correctly maps fields and handles optional attributes."""
    mock_spec = MagicMock()
    mock_spec.scenario_id = "mock_scen_123"
    mock_spec.to_scenario_dict.return_value = {
        "motion": {"motion_type": "STRAIGHT_LINE", "speed": 40.0},
        "atmospheric": {"condition": "HAZE"},
    }

    mock_eval = MagicMock(spec=EvaluationRunResult)
    mock_eval.algorithm_fps = 310.5
    mock_eval.centroid_rmse = 0.045
    mock_eval.target_loss_rate = 0.0
    mock_eval.acquisition_time_s = 0.033
    mock_eval.outcome = EvaluationOutcome.SUCCESS
    mock_eval.passed_sih_spec = True
    mock_eval.json_report_path = "output/ai_scenarios/mock_eval.json"

    with patch.object(AIScenarioWorkflow, "execute_prompt", return_value=(True, mock_spec, mock_eval, [])):
        res = run_ai_scenario(AIScenarioRequest(prompt="Linear test prompt"))

        assert res["valid"] is True
        assert res["scenario_id"] == "mock_scen_123"
        assert res["validation_errors"] == []
        assert res["spec"]["motion"]["motion_type"] == "STRAIGHT_LINE"
        assert res["evaluation"]["algorithm_fps"] == 310.5
        assert res["evaluation"]["centroid_rmse"] == 0.045
        assert res["evaluation"]["passed_sih_spec"] is True
        assert res["report_path"] == "output/ai_scenarios/mock_eval.json"
