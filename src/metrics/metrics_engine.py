"""
Metrics Engine — Module 15 per Architecture v1.2 §15.

Computes performance metrics from tracker output and (when available) ground truth.
Definitions are provisional and replaceable.
"""

from __future__ import annotations

import math
from typing import Optional, List

from src.frame.data_contracts import (
    TrackerOutput,
    GroundTruth,
    MetricsSummary,
    TrackingState,
)


class MetricsEngine:
    """
    Computes all performance metrics dynamically.
    """

    def __init__(self, run_id: str = "") -> None:
        self.run_id = run_id
        self.total_frames = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        self.valid_detections = 0
        self.total_candidate_count = 0
        self.total_processing_time_ms = 0.0
        self.processing_times: List[float] = []

        self.centroid_errors_ideal: List[float] = []
        self.centroid_errors_rendered: List[float] = []
        self.tracking_errors: List[float] = []

        self.frames_locked = 0
        self.frames_lost = 0

        self.acquisition_time_s: Optional[float] = None
        self.reacquisition_times: List[float] = []
        self.reacq_start_time: Optional[float] = None

    def update(
        self,
        tracker_output: TrackerOutput,
        ground_truth: Optional[GroundTruth] = None,
        camera_width: int = 640,
        camera_height: int = 480
    ) -> None:
        """Process one frame's results and update running statistics."""
        self.total_frames += 1
        
        if self.start_time is None:
            self.start_time = tracker_output.timestamp
        self.end_time = tracker_output.timestamp

        self.total_processing_time_ms += tracker_output.processing_time_ms
        self.processing_times.append(tracker_output.processing_time_ms)

        if tracker_output.detection_valid:
            self.valid_detections += 1
        self.total_candidate_count += tracker_output.candidate_count

        # Compute tracking error (distance to center of frame)
        if tracker_output.state == TrackingState.TRACKING and tracker_output.track is not None:
            self.frames_locked += 1
            cx, cy = camera_width / 2.0, camera_height / 2.0
            tx, ty = tracker_output.track.estimated_x, tracker_output.track.estimated_y
            err = math.hypot(tx - cx, ty - cy)
            self.tracking_errors.append(err)
        elif tracker_output.state == TrackingState.LOST:
            self.frames_lost += 1

        # Acquisition timing
        if tracker_output.state == TrackingState.TRACKING and tracker_output.previous_state == TrackingState.ACQUIRING:
            if self.acquisition_time_s is None:
                self.acquisition_time_s = tracker_output.timestamp - self.start_time
            elif self.reacq_start_time is None:
                # If we transitioned from LOST -> REACQUIRING -> TRACKING
                pass # Usually reacq_start_time is set when state becomes LOST

        if tracker_output.state == TrackingState.LOST and tracker_output.previous_state == TrackingState.TRACKING:
            self.reacq_start_time = tracker_output.timestamp

        if tracker_output.state == TrackingState.TRACKING and tracker_output.previous_state == TrackingState.REACQUIRING:
            if self.reacq_start_time is not None:
                self.reacquisition_times.append(tracker_output.timestamp - self.reacq_start_time)
                self.reacq_start_time = None

        # Compute centroiding error if ground truth is available
        if ground_truth is not None and tracker_output.centroid is not None and tracker_output.centroid.valid:
            cx, cy = tracker_output.centroid.x, tracker_output.centroid.y
            
            if ground_truth.ideal_projected_x is not None and ground_truth.ideal_projected_y is not None:
                ideal_err = math.hypot(cx - ground_truth.ideal_projected_x, cy - ground_truth.ideal_projected_y)
                self.centroid_errors_ideal.append(ideal_err)
                
            if ground_truth.rendered_centroid_x is not None and ground_truth.rendered_centroid_y is not None:
                rend_err = math.hypot(cx - ground_truth.rendered_centroid_x, cy - ground_truth.rendered_centroid_y)
                self.centroid_errors_rendered.append(rend_err)

    def get_summary(self) -> MetricsSummary:
        """Aggregate current statistics into a MetricsSummary object."""
        duration = 0.0
        if self.start_time is not None and self.end_time is not None:
            duration = self.end_time - self.start_time

        mean_fps = 0.0
        if duration > 0:
            mean_fps = self.total_frames / duration

        mean_latency = 0.0
        max_latency = 0.0
        p95_latency = 0.0
        if self.processing_times:
            mean_latency = self.total_processing_time_ms / len(self.processing_times)
            max_latency = max(self.processing_times)
            sorted_times = sorted(self.processing_times)
            p95_latency = sorted_times[int(len(sorted_times) * 0.95)]

        detection_rate = (self.valid_detections / self.total_frames) if self.total_frames > 0 else 0.0
        mean_candidates = (self.total_candidate_count / self.total_frames) if self.total_frames > 0 else 0.0

        # Centroiding errors (we use rendered as primary if available, else ideal)
        errors = self.centroid_errors_rendered if self.centroid_errors_rendered else self.centroid_errors_ideal
        mean_ce = sum(errors) / len(errors) if errors else 0.0
        max_ce = max(errors) if errors else 0.0
        rmse_ce = math.sqrt(sum(e*e for e in errors) / len(errors)) if errors else 0.0
        
        median_ce = 0.0
        pct_1, pct_2, pct_5 = 0.0, 0.0, 0.0
        if errors:
            sorted_e = sorted(errors)
            median_ce = sorted_e[len(sorted_e) // 2]
            pct_1 = sum(1 for e in errors if e <= 1.0) / len(errors) * 100
            pct_2 = sum(1 for e in errors if e <= 2.0) / len(errors) * 100
            pct_5 = sum(1 for e in errors if e <= 5.0) / len(errors) * 100

        # Tracking errors
        mean_te = sum(self.tracking_errors) / len(self.tracking_errors) if self.tracking_errors else 0.0
        max_te = max(self.tracking_errors) if self.tracking_errors else 0.0

        lock_retention = (self.frames_locked / self.total_frames * 100) if self.total_frames > 0 else 0.0
        target_loss = (self.frames_lost / self.total_frames * 100) if self.total_frames > 0 else 0.0

        mean_reacq = sum(self.reacquisition_times) / len(self.reacquisition_times) if self.reacquisition_times else None
        max_reacq = max(self.reacquisition_times) if self.reacquisition_times else None

        return MetricsSummary(
            run_id=self.run_id,
            total_frames=self.total_frames,
            duration_seconds=duration,
            detection_rate=detection_rate,
            false_positive_rate=0.0, # requires more complex truth matching
            mean_candidate_count=mean_candidates,
            mean_detection_latency_ms=mean_latency,
            mean_centroid_error=mean_ce,
            median_centroid_error=median_ce,
            rmse_centroid=rmse_ce,
            max_centroid_error=max_ce,
            pct_within_1px=pct_1,
            pct_within_2px=pct_2,
            pct_within_5px=pct_5,
            mean_tracking_error=mean_te,
            max_tracking_error=max_te,
            lock_retention_rate=lock_retention,
            target_loss_rate=target_loss,
            track_continuity=lock_retention,
            acquisition_time_s=self.acquisition_time_s,
            reacquisition_events=len(self.reacquisition_times),
            mean_reacquisition_time_s=mean_reacq,
            max_reacquisition_time_s=max_reacq,
            mean_fps=mean_fps,
            mean_latency_ms=mean_latency,
            p95_latency_ms=p95_latency,
            max_latency_ms=max_latency,
            mean_steady_state_error=mean_te,
            oscillation_measure=0.0
        )
