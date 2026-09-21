"""
Regression tests for DEF-01 (Packaged Plugin Discovery) and DEF-02 (CLI Matrix/AI Dispatch).
Verifies:
  1. DEF-01: lumitrack.spec contains the plugin algorithms directory in added_files datas.
  2. DEF-01: Packaged plugin directory exists and contains baseline_tracker manifest.
  3. DEF-02: CLI argparser accepts valid --matrix choices and --ai-scenario strings.
  4. DEF-02: CLI argparser rejects invalid matrix choices.
  5. DEF-02: main() dispatches --matrix to BenchmarkManager.run_benchmark_matrix.
  6. DEF-02: main() dispatches --ai-scenario to BenchmarkManager.run_ai_scenario.
  7. DEF-02: main() exits with code 1 when AI scenario prompt fails validation.
"""

import os
import sys
import unittest.mock as mock
import pytest

from src.main import parse_args, main


def test_def01_spec_file_contains_plugin_algorithms():
    """DEF-01: Verify lumitrack.spec bundles src/plugins/algorithms into package datas."""
    spec_path = "lumitrack.spec"
    assert os.path.isfile(spec_path), f"lumitrack.spec not found at {spec_path}"

    with open(spec_path, "r", encoding="utf-8") as f:
        spec_content = f.read()

    assert "('src/plugins/algorithms', 'src/plugins/algorithms')" in spec_content, (
        "lumitrack.spec must include ('src/plugins/algorithms', 'src/plugins/algorithms') in added_files"
    )


def test_def01_packaged_plugin_directory_structure():
    """DEF-01: Verify packaged dist contains baseline_tracker in expected internal path."""
    internal_plugin_dir = os.path.join(
        "dist", "LumiTrack", "_internal", "src", "plugins", "algorithms", "baseline_tracker"
    )
    manifest_path = os.path.join(internal_plugin_dir, "manifest.json")
    tracker_py = os.path.join(internal_plugin_dir, "baseline_tracker.py")

    assert os.path.isfile(manifest_path), f"Packaged plugin manifest missing: {manifest_path}"
    assert os.path.isfile(tracker_py), f"Packaged plugin code missing: {tracker_py}"


def test_def02_cli_parser_matrix_choices():
    """DEF-02: Verify CLI argparser parses valid matrix subsets."""
    for choice in ["SMOKE", "CORE", "DISTURBANCE", "FULL"]:
        args = parse_args(["--matrix", choice])
        assert args.matrix == choice


def test_def02_cli_parser_matrix_invalid_choice():
    """DEF-02: Verify CLI argparser rejects invalid matrix subset."""
    with pytest.raises(SystemExit):
        parse_args(["--matrix", "NONEXISTENT_SUBSET"])


def test_def02_cli_parser_ai_scenario():
    """DEF-02: Verify CLI argparser parses --ai-scenario string."""
    prompt = "Circular orbit with low turbulence and 20 px/s speed"
    args = parse_args(["--ai-scenario", prompt])
    assert args.ai_scenario == prompt


def test_def02_main_dispatch_matrix():
    """DEF-02: Verify main() dispatches --matrix to BenchmarkManager.run_benchmark_matrix."""
    mock_bm_result = mock.MagicMock()
    mock_bm_result.total_runs = 3
    mock_bm_result.successful_runs = 3
    mock_bm_result.failed_runs = 0
    mock_bm_result.crashed_runs = 0
    mock_bm_result.mean_algorithm_fps = 450.0
    mock_bm_result.mean_rmse_centroid = 0.0
    mock_bm_result.passed_sih_spec = True

    with mock.patch("src.main.BenchmarkManager") as MockBM:
        mock_bm_instance = MockBM.return_value
        mock_bm_instance.run_benchmark_matrix.return_value = mock_bm_result
        mock_bm_instance.generate_comprehensive_report.return_value = ("report.json", "report.csv", "report.md")

        with pytest.raises(SystemExit) as excinfo:
            main(["--matrix", "SMOKE", "--max-frames", "5"])

        assert excinfo.value.code == 0
        mock_bm_instance.run_benchmark_matrix.assert_called_once()
        call_kwargs = mock_bm_instance.run_benchmark_matrix.call_args[1]
        assert call_kwargs["subset"] == "SMOKE"
        assert call_kwargs["max_frames"] == 5


def test_def02_main_dispatch_ai_scenario():
    """DEF-02: Verify main() dispatches --ai-scenario to BenchmarkManager.run_ai_scenario."""
    mock_spec = mock.MagicMock()
    mock_spec.scenario_id = "test_scenario"
    mock_spec.trajectory_type = "CIRCULAR"
    mock_spec.target_speed = 20.0
    mock_spec.atmospheric_condition = "CLEAR"

    mock_res = mock.MagicMock()
    mock_res.outcome.value = "SUCCESS"
    mock_res.total_frames = 50
    mock_res.algorithm_fps = 120.0
    mock_res.centroid_rmse = 0.5
    mock_res.target_loss_rate = 0.0
    mock_res.json_report_path = "output/test.json"

    with mock.patch("src.main.BenchmarkManager") as MockBM:
        mock_bm_instance = MockBM.return_value
        mock_bm_instance.run_ai_scenario.return_value = (True, mock_spec, mock_res, [])

        with pytest.raises(SystemExit) as excinfo:
            main(["--ai-scenario", "Circular orbit scenario", "--max-frames", "20"])

        assert excinfo.value.code == 0
        mock_bm_instance.run_ai_scenario.assert_called_once()
        call_kwargs = mock_bm_instance.run_ai_scenario.call_args[1]
        assert call_kwargs["prompt"] == "Circular orbit scenario"
        assert call_kwargs["max_frames"] == 20


def test_def02_main_dispatch_ai_scenario_rejection():
    """DEF-02: Verify main() exits with code 1 when AI scenario is rejected by validator."""
    with mock.patch("src.main.BenchmarkManager") as MockBM:
        mock_bm_instance = MockBM.return_value
        mock_bm_instance.run_ai_scenario.return_value = (False, None, None, ["Out of speed boundary"])

        with pytest.raises(SystemExit) as excinfo:
            main(["--ai-scenario", "Hypersonic 999 px/s target"])

        assert excinfo.value.code == 1
