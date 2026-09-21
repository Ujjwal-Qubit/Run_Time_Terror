"""
Logging Engine — Module 16 per Architecture v1.2 §14 and §16.

Provides per-frame telemetry logging (CSV), evaluator centroid export (CSV),
summary report (JSON), and formatted performance scorecard (Markdown/Text).
Designed to be non-blocking — uses in-memory buffering and deferred flushing
to ensure "Logging must not destroy FPS."
"""

from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict, fields
from typing import List, Optional, IO, Tuple, Dict, Any

from src.frame.data_contracts import (
    TelemetryRecord,
    MetricsSummary,
    GrandEvaluationSummary,
)


class LoggingEngine:
    """
    Logging Engine — Module 16.

    Responsibilities:
      - Buffer per-frame TelemetryRecords in memory
      - Stream CSV logs on flush or finalize
      - Export evaluator-formatted centroid CSV matching PS Line 113
      - Write JSON summary on finalize
      - Auto-generate performance report scorecard
      - Zero expensive synchronous disk I/O in the core tracking loop
    """

    def __init__(self, output_dir: str = "output", run_id: str = "") -> None:
        self._output_dir = output_dir
        self._run_id = run_id or f"run_{int(time.time())}"
        self._buffer: List[TelemetryRecord] = []
        self._csv_file: Optional[IO] = None
        self._csv_writer: Optional[csv.DictWriter] = None
        self._centroid_file: Optional[IO] = None
        self._centroid_writer: Optional[csv.writer] = None
        self._initialized = False

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def output_dir(self) -> str:
        return self._output_dir

    def initialize(self) -> None:
        """Create output directory and open CSV files."""
        os.makedirs(self._output_dir, exist_ok=True)

        # 1. Full Telemetry CSV
        csv_path = os.path.join(
            self._output_dir, f"{self._run_id}_telemetry.csv"
        )
        self._csv_file = open(csv_path, "w", newline="")
        field_names = [f.name for f in fields(TelemetryRecord)]
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=field_names)
        self._csv_writer.writeheader()

        # 2. Evaluator Centroid Export CSV (PS Line 113 format)
        centroid_path = os.path.join(
            self._output_dir, f"{self._run_id}_centroids.csv"
        )
        self._centroid_file = open(centroid_path, "w", newline="")
        self._centroid_writer = csv.writer(self._centroid_file)
        self._centroid_writer.writerow([
            "frame_number", "centroid_x", "centroid_y", "is_valid", "confidence"
        ])

        self._initialized = True

    def log_frame(self, record: TelemetryRecord) -> None:
        """
        Buffer a per-frame telemetry record.
        Non-blocking append during hot loop execution.
        """
        self._buffer.append(record)

    def flush(self) -> None:
        """Write buffered records to CSV files. Called periodically or on demand."""
        if not self._initialized:
            return

        if self._csv_writer:
            for record in self._buffer:
                self._csv_writer.writerow(asdict(record))

        if self._centroid_writer:
            for record in self._buffer:
                cx_str = f"{record.estimated_centroid_x:.4f}" if record.estimated_centroid_x is not None else ""
                cy_str = f"{record.estimated_centroid_y:.4f}" if record.estimated_centroid_y is not None else ""
                self._centroid_writer.writerow([
                    record.frame_number,
                    cx_str,
                    cy_str,
                    1 if record.centroid_valid else 0,
                    f"{record.detection_confidence:.4f}",
                ])

        self._buffer.clear()

        if self._csv_file:
            self._csv_file.flush()
        if self._centroid_file:
            self._centroid_file.flush()

    def write_summary(self, summary: MetricsSummary) -> str:
        """Write the aggregate metrics summary as JSON."""
        summary_path = os.path.join(
            self._output_dir, f"{self._run_id}_summary.json"
        )
        with open(summary_path, "w") as f:
            json.dump(asdict(summary), f, indent=2)
        return summary_path

    def write_config_snapshot(self, config_dict: dict) -> str:
        """Write the configuration snapshot used for this run."""
        config_path = os.path.join(
            self._output_dir, f"{self._run_id}_config.json"
        )
        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2)
        return config_path

    def write_performance_report(self, summary: MetricsSummary) -> str:
        """
        Auto-generate a human-readable markdown performance report scorecard.
        Per PS Section Deliverables (Line 103).
        """
        report_path = os.path.join(
            self._output_dir, f"{self._run_id}_performance_report.md"
        )

        acq_status = "PASS" if summary.acquisition_time_s is not None and summary.acquisition_time_s <= 2.0 else "FAIL"
        reacq_status = (
            "PASS"
            if (summary.mean_reacquisition_time_s is None or summary.mean_reacquisition_time_s <= 1.0)
            else "FAIL"
        )
        track_err_status = "PASS" if summary.mean_tracking_error <= 10.0 else "FAIL"
        loss_status = "PASS" if summary.target_loss_rate < 5.0 else "FAIL"
        fps_status = "PASS" if summary.mean_fps >= 20.0 else "FAIL"

        acq_str = f"{summary.acquisition_time_s:.2f}" if summary.acquisition_time_s is not None else "N/A"
        reacq_str = f"{summary.mean_reacquisition_time_s:.2f}" if summary.mean_reacquisition_time_s is not None else "N/A"
        max_reacq_str = f"{summary.max_reacquisition_time_s:.2f}" if summary.max_reacquisition_time_s is not None else "N/A"

        lines = [
            f"# SIH 2026 Virtual Camera Tracking System — Performance Report",
            f"",
            f"- **Run ID:** `{summary.run_id}`",
            f"- **Total Frames Processed:** `{summary.total_frames}`",
            f"- **Total Simulation Duration:** `{summary.duration_seconds:.2f} s`",
            f"- **Mean Processing Throughput:** `{summary.mean_fps:.1f} FPS`",
            f"",
            f"## 1. Compliance Scorecard (PS 26169 Thresholds)",
            f"",
            f"| Metric | Specification | Measured Value | Compliance |",
            f"| :--- | :--- | :--- | :--- |",
            f"| **Acquisition Time** | $\\le 2.0$ s | `{acq_str}` s | **{acq_status}** |",
            f"| **Tracking Error** | $\\le 10.0$ px | `{summary.mean_tracking_error:.2f}` px (max: `{summary.max_tracking_error:.2f}` px) | **{track_err_status}** |",
            f"| **Target Loss Rate** | $< 5.0\\%$ | `{summary.target_loss_rate:.2f}\\%` | **{loss_status}** |",
            f"| **Reacquisition Time** | $\\le 1.0$ s | `{reacq_str}` s | **{reacq_status}** |",
            f"| **Processing Speed** | $\\ge 20.0$ FPS | `{summary.mean_fps:.1f}` FPS | **{fps_status}** |",
            f"",
            f"## 2. Accuracy & Sub-Pixel Localization",
            f"",
            f"- **RMSE Centroiding Error (Rendered):** `{summary.rmse_centroid_rendered:.3f}` px",
            f"- **RMSE Centroiding Error (Ideal):** `{summary.rmse_centroid_ideal:.3f}` px",
            f"- **Mean Centroiding Error:** `{summary.mean_centroid_error:.3f}` px",
            f"- **Median Centroiding Error:** `{summary.median_centroid_error:.3f}` px",
            f"- **Centroid Error $< 1$ px:** `{summary.pct_within_1px:.1f}\\%`",
            f"- **Centroid Error $< 2$ px:** `{summary.pct_within_2px:.1f}\\%`",
            f"- **Centroid Error $< 5$ px:** `{summary.pct_within_5px:.1f}\\%`",
            f"",
            f"## 3. Tracking Continuity & Lock Retention",
            f"",
            f"- **Lock Retention (Post-Acquisition):** `{summary.lock_retention_post_acq_pct:.2f}\\%`",
            f"- **Lock Retention (All Frames):** `{summary.lock_retention_all_pct:.2f}\\%`",
            f"- **Lock Retention (When Visible):** `{summary.lock_retention_visible_pct:.2f}\\%`",
            f"- **Track Continuity Ratio:** `{summary.track_continuity:.3f}`",
            f"- **Reacquisition Episodes:** `{summary.reacquisition_events}`",
            f"- **Max Reacquisition Time:** `{max_reacq_str}` s",
            f"",
            f"## 4. Latency Distribution (End-to-End Frame Processing)",
            f"",
            f"- **Mean Latency:** `{summary.mean_latency_ms:.2f}` ms",
            f"- **Median (P50) Latency:** `{summary.p50_latency_ms:.2f}` ms",
            f"- **95th Percentile (P95):** `{summary.p95_latency_ms:.2f}` ms",
            f"- **99th Percentile (P99):** `{summary.p99_latency_ms:.2f}` ms",
            f"- **Max Frame Latency:** `{summary.max_latency_ms:.2f}` ms",
            f"",
            f"## 5. PTZ Camera Actuation",
            f"",
            f"- **Steady-State Mean Error:** `{summary.mean_steady_state_error:.2f}` px",
            f"- **Oscillation (Std Dev):** `{summary.oscillation_measure:.3f}` px",
            f"- **Frames in Deadband:** `{summary.frames_in_deadband_pct:.1f}\\%`",
        ]

        with open(report_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        return report_path

    def finalize(self) -> None:
        """Flush remaining records and close all active file handles."""
        self.flush()
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
        if self._centroid_file:
            self._centroid_file.close()
            self._centroid_file = None
        self._initialized = False

    def get_buffer_size(self) -> int:
        """Return current buffer size (for monitoring)."""
        return len(self._buffer)

    @staticmethod
    def write_grand_summary(
        grand_summary: GrandEvaluationSummary,
        output_dir: str = "output"
    ) -> Tuple[str, str]:
        """
        Export grand evaluation scorecard as JSON and Markdown.
        Returns (json_path, markdown_path).
        """
        os.makedirs(output_dir, exist_ok=True)
        batch_id = grand_summary.batch_id or f"batch_{int(time.time())}"

        # 1. Export JSON Summary
        json_path = os.path.join(output_dir, f"{batch_id}_grand_summary.json")
        with open(json_path, "w") as f:
            json.dump(asdict(grand_summary), f, indent=2)

        # 2. Export Markdown Scorecard
        md_path = os.path.join(output_dir, f"{batch_id}_grand_evaluator_report.md")

        fps_status = "PASS" if grand_summary.passed_fps_spec else "FAIL"
        acq_status = "PASS" if grand_summary.passed_acquisition_spec else "FAIL"
        err_status = "PASS" if grand_summary.passed_tracking_error_spec else "FAIL"
        loss_status = "PASS" if grand_summary.passed_loss_rate_spec else "FAIL"
        overall_status = "PASSED" if grand_summary.overall_compliance else "FAILED"

        acq_str = f"{grand_summary.mean_acquisition_time_s:.2f}" if grand_summary.mean_acquisition_time_s is not None else "N/A"

        lines = [
            f"# SIH 2026 Virtual Camera Tracking System — Grand Evaluation Scorecard",
            f"",
            f"- **Batch ID:** `{batch_id}`",
            f"- **Batch Evaluation Type:** `{grand_summary.batch_type}`",
            f"- **Total Sequences:** `{grand_summary.total_runs}` (Successful: `{grand_summary.successful_runs}`, Failed: `{grand_summary.failed_runs}`)",
            f"- **Total Frames Processed:** `{grand_summary.total_frames_processed}`",
            f"- **Total Simulated Time:** `{grand_summary.total_duration_s:.2f} s`",
            f"- **Overall Benchmark Compliance:** **{overall_status}**",
            f"",
            f"## 1. Compliance Scorecard (PS 26169 Thresholds)",
            f"",
            f"| Metric | Specification | Measured (Macro Mean) | Compliance |",
            f"| :--- | :--- | :--- | :--- |",
            f"| **Processing Speed** | $\\ge 20.0$ FPS | `{grand_summary.mean_fps:.1f}` FPS | **{fps_status}** |",
            f"| **Acquisition Time** | $\\le 2.0$ s | `{acq_str}` s | **{acq_status}** |",
            f"| **Tracking Error** | $\\le 10.0$ px | `{grand_summary.mean_tracking_error:.2f}` px | **{err_status}** |",
            f"| **Target Loss Rate** | $< 5.0\\%$ | `{grand_summary.mean_target_loss_rate_pct:.2f}\\%` | **{loss_status}** |",
            f"",
            f"## 2. Sequence-by-Sequence Breakdown",
            f"",
            f"| Run / Item ID | Status | Frames | FPS | Acq Time (s) | Centroid RMSE (px) | Tracking Error (px) | Lock Ret (%) |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for item in grand_summary.run_items:
            if item.success and item.summary:
                s = item.summary
                acq_val = f"{s.acquisition_time_s:.2f}" if s.acquisition_time_s is not None else "N/A"
                rmse_val = s.rmse_centroid if s.rmse_centroid > 0.0 else s.rmse_centroid_rendered
                lines.append(
                    f"| `{item.item_id}` | SUCCESS | `{s.total_frames}` | `{s.mean_fps:.1f}` | "
                    f"`{acq_val}` | `{rmse_val:.3f}` | `{s.mean_tracking_error:.2f}` | "
                    f"`{s.lock_retention_post_acq_pct:.1f}%` |"
                )
            else:
                err_msg = item.error_message or "Execution failed"
                lines.append(
                    f"| `{item.item_id}` | **FAILED** (`{err_msg}`) | - | - | - | - | - | - |"
                )

        lines.extend([
            f"",
            f"## 3. Macro Performance & Sub-Pixel Localization",
            f"",
            f"- **Mean Centroiding RMSE (Rendered):** `{grand_summary.mean_rmse_centroid_rendered:.3f}` px",
            f"- **Mean Centroiding RMSE:** `{grand_summary.mean_rmse_centroid:.3f}` px",
            f"- **Mean Tracking Error:** `{grand_summary.mean_tracking_error:.2f}` px",
            f"- **Mean Lock Retention Rate:** `{grand_summary.mean_lock_retention_pct:.2f}%`",
            f"- **Mean Target Loss Rate:** `{grand_summary.mean_target_loss_rate_pct:.2f}%`",
            f"- **Mean Pipeline Latency:** `{grand_summary.mean_latency_ms:.2f}` ms",
            f"- **95th Percentile Latency (P95):** `{grand_summary.p95_latency_ms:.2f}` ms",
        ])

        if grand_summary.failed_runs > 0:
            lines.extend([
                f"",
                f"## 4. Execution Failures",
                f"",
            ])
            for item in grand_summary.run_items:
                if not item.success:
                    lines.append(f"- **`{item.item_id}`**: `{item.error_message}` (Source: `{item.source_path}`)")

        with open(md_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        return (json_path, md_path)

