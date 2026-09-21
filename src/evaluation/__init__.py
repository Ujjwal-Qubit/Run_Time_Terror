"""
Evaluation Subsystem — Module 17 (Architecture v1.2 §17).

Coordinates Benchmark-1 (Simulation) and Benchmark-2 (MP4) execution,
batch automated evaluations, and algorithm comparative harness testing.
"""

from src.evaluation.benchmark_manager import BenchmarkManager
from src.evaluation.harness import (
    EvaluationHarness,
    EvaluationExperiment,
    EvaluationOutcome,
    EvaluationRunResult,
    ComparisonSummary,
)
from src.evaluation.matrix import (
    BenchmarkSubset,
    BenchmarkScenarioDefinition,
    StandardBenchmarkMatrix,
    BenchmarkMatrixResults,
    BenchmarkMatrixRunner,
)
from src.evaluation.reporting import (
    ComprehensiveReportGenerator,
    FailureAnalysisSummary,
    FailureEpisode,
)
from src.evaluation.ai_scenario import (
    CandidateScenarioSpec,
    ValidatedScenarioSpec,
    ScenarioSpecificationValidator,
    AIInterpretationEngine,
    DeterministicTrajectoryGenerator,
    AIScenarioWorkflow,
)

__all__ = [
    "BenchmarkManager",
    "EvaluationHarness",
    "EvaluationExperiment",
    "EvaluationOutcome",
    "EvaluationRunResult",
    "ComparisonSummary",
    "BenchmarkSubset",
    "BenchmarkScenarioDefinition",
    "StandardBenchmarkMatrix",
    "BenchmarkMatrixResults",
    "BenchmarkMatrixRunner",
    "ComprehensiveReportGenerator",
    "FailureAnalysisSummary",
    "FailureEpisode",
    "CandidateScenarioSpec",
    "ValidatedScenarioSpec",
    "ScenarioSpecificationValidator",
    "AIInterpretationEngine",
    "DeterministicTrajectoryGenerator",
    "AIScenarioWorkflow",
]


