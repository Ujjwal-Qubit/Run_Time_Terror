"""
Logging Engine — Module 16 per Architecture v1.2 §16.

Provides per-frame telemetry logging (CSV) and summary report (JSON).
Designed to be non-blocking — uses in-memory buffer and writes on
flush/finalize to avoid corrupting benchmark timing.

Per Architecture v1.2: "Logging must not destroy FPS."
"""

from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict, fields
from typing import List, Optional, IO

from src.frame.data_contracts import TelemetryRecord, MetricsSummary


class LoggingEngine:
    """
    Logging Engine — Module 16.

    Responsibilities:
      - Buffer per-frame TelemetryRecords in memory
      - Write CSV on flush or finalize
      - Write JSON summary on finalize
      - Do NOT perform expensive I/O during the hot loop
    """

    def __init__(self, output_dir: str = "output", run_id: str = "") -> None:
        self._output_dir = output_dir
        self._run_id = run_id or f"run_{int(time.time())}"
        self._buffer: List[TelemetryRecord] = []
        self._csv_file: Optional[IO] = None
        self._csv_writer: Optional[csv.DictWriter] = None
        self._initialized = False

    @property
    def run_id(self) -> str:
        return self._run_id

    def initialize(self) -> None:
        """Create output directory and open CSV file."""
        os.makedirs(self._output_dir, exist_ok=True)
        csv_path = os.path.join(
            self._output_dir, f"{self._run_id}_telemetry.csv"
        )
        self._csv_file = open(csv_path, "w", newline="")
        field_names = [f.name for f in fields(TelemetryRecord)]
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=field_names)
        self._csv_writer.writeheader()
        self._initialized = True

    def log_frame(self, record: TelemetryRecord) -> None:
        """
        Buffer a per-frame telemetry record.
        This is called from the hot loop — must be fast.
        """
        self._buffer.append(record)

    def flush(self) -> None:
        """Write buffered records to CSV. Called periodically or on demand."""
        if not self._initialized or not self._csv_writer:
            return

        for record in self._buffer:
            self._csv_writer.writerow(asdict(record))

        self._buffer.clear()

        if self._csv_file:
            self._csv_file.flush()

    def write_summary(self, summary: MetricsSummary) -> None:
        """Write the aggregate metrics summary as JSON."""
        summary_path = os.path.join(
            self._output_dir, f"{self._run_id}_summary.json"
        )
        with open(summary_path, "w") as f:
            json.dump(asdict(summary), f, indent=2)

    def write_config_snapshot(self, config_dict: dict) -> None:
        """Write the configuration snapshot used for this run."""
        config_path = os.path.join(
            self._output_dir, f"{self._run_id}_config.json"
        )
        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2)

    def finalize(self) -> None:
        """Flush remaining records and close files."""
        self.flush()
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
        self._initialized = False

    def get_buffer_size(self) -> int:
        """Return current buffer size (for monitoring)."""
        return len(self._buffer)
