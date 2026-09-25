"""
Dataset Manifest — Dataset metadata and version tracking.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List


class DatasetManifest:
    """
    Creates and manages dataset manifest JSON files.
    """

    def __init__(
        self,
        dataset_name: str,
        dataset_version: str = "v1.0",
        task: str = "candidate_classification",
        git_commit: str = "HEAD",
        seed: int = 42,
    ) -> None:
        self.dataset_name = dataset_name
        self.dataset_version = dataset_version
        self.task = task
        self.git_commit = git_commit
        self.seed = seed
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def save(self, output_dir: str, num_records: int, scenarios: List[str]) -> str:
        manifest_data = {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "task": self.task,
            "git_commit": self.git_commit,
            "seed": self.seed,
            "created_at": self.created_at,
            "num_records": num_records,
            "scenarios": scenarios,
        }
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, "manifest.json")
        with open(filepath, "w") as f:
            json.dump(manifest_data, f, indent=2)
        return filepath
