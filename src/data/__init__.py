"""
Data Package — Dataset generation, schema, manifest, and split building.
"""

from src.data.dataset_schema import CandidateDatasetRecord, TemporalSequenceRecord
from src.data.dataset_manifest import DatasetManifest
from src.data.split_builder import SplitBuilder

__all__ = [
    "CandidateDatasetRecord",
    "TemporalSequenceRecord",
    "DatasetManifest",
    "SplitBuilder",
]
