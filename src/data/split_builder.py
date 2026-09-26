"""
Split Builder — Grouped scenario train/val/test split manager per Runbook §3.
Prevents data leakage by ensuring adjacent frames from the same scenario stay together.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple
import numpy as np


class SplitBuilder:
    """
    Splits dataset records into Train (60%), Validation (20%), and Test (20%)
    grouped strictly by scenario/sequence ID to prevent trajectory data leakage.
    """

    @staticmethod
    def build_split(
        records: List[Dict[str, Any]],
        group_key: str = "run_id",
        seed: int = 42,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split records by group_key.
        """
        if not 0.0 < train_ratio < 1.0 or not 0.0 < val_ratio < 1.0:
            raise ValueError("train_ratio and val_ratio must be between 0 and 1")
        if train_ratio + val_ratio >= 1.0:
            raise ValueError("train_ratio + val_ratio must leave a non-empty test split")

        # Group records by scenario / run_id
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in records:
            key = r.get(group_key, "default")
            groups.setdefault(key, []).append(r)

        group_keys = list(groups.keys())
        rng = np.random.RandomState(seed)
        rng.shuffle(group_keys)

        n_groups = len(group_keys)
        if n_groups < 3:
            raise ValueError("At least three distinct groups are required for train/validation/test splits")

        n_train = max(1, int(round(n_groups * train_ratio)))
        n_val = max(1, int(round(n_groups * val_ratio)))
        while n_train + n_val >= n_groups:
            if n_val > 1:
                n_val -= 1
            elif n_train > 1:
                n_train -= 1
            else:
                raise ValueError("Unable to allocate non-empty train/validation/test group splits")

        train_keys = set(group_keys[:n_train])
        val_keys = set(group_keys[n_train : n_train + n_val])
        test_keys = set(group_keys[n_train + n_val :])

        train_records = [r for r in records if r.get(group_key) in train_keys]
        val_records = [r for r in records if r.get(group_key) in val_keys]
        test_records = [r for r in records if r.get(group_key) in test_keys]

        return train_records, val_records, test_records

    @staticmethod
    def save_splits(
        output_dir: str,
        train_records: List[Dict[str, Any]],
        val_records: List[Dict[str, Any]],
        test_records: List[Dict[str, Any]],
    ) -> None:
        os.makedirs(output_dir, exist_ok=True)
        for name, data in [("train.json", train_records), ("val.json", val_records), ("test.json", test_records)]:
            with open(os.path.join(output_dir, name), "w") as f:
                json.dump(data, f, indent=2)
