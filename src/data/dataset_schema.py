"""
Dataset Schema — JSON schema definitions for offline candidate and temporal datasets.

Per Spec §8 & Runbook §3.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CandidateDatasetRecord:
    """
    Candidate classification dataset record.
    """

    dataset_version: str
    run_id: str
    frame_number: int
    candidate_id: int
    features: Dict[str, float]
    label: int                  # 1 = beacon, 0 = noise
    label_definition: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TemporalSequenceRecord:
    """
    Temporal prediction dataset record.
    """

    dataset_version: str
    sequence_id: str
    frame_number: int
    input_history: List[Dict[str, Any]]
    target: Dict[str, float]
    label_source: str
    scenario: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
