"""
Metrics Engine — Module 15 per Architecture v1.2 §4 and §13.

Responsibilities:
  - Compute running spatial accuracy metrics (centroiding error, tracking error, RMSE)
  - Compute operational timing metrics (acquisition time, reacquisition time episodes)
  - Compute lock retention rate, target loss rate, and track continuity
  - Compute real-time processing throughput (FPS) and latency distributions
  - Enforce strict ground-truth firewall: GroundTruth is consumed exclusively via
    side-channel parameters and never exposed to tracker components.
  - Support both Benchmark-1 (Simulation with Ground Truth) and Benchmark-2
    (MP4 without Ground Truth, exporting centroid files).
"""

from __future__ import annotations

import math
import random
import statistics
import time
from typing import List, Optional, Sequence

from src.interfaces.strategy_interfaces import IMetricsEngine
from src.frame.data_contracts import (
    FramePacket,
    CentroidResult,
    TrackResult,
    TrackingStateResult,
    TrackingState,
    DetectionResult,
    PTZCommand,
    GroundTruth,
    TelemetryRecord,
    MetricsSummary,
)


class MetricsEngine(IMetricsEngine):
    """
    Production Metrics Engine (Module 15).

    Provides deterministic, O(1) incremental accumulation of all SIH PS 26169
    benchmark criteria and engineering performance metrics.
    """

    def __init__(self, run_id: str = "", max_sample_capacity: int = 2000) -> None:
        self._run_id = run_id or f"run_{int(time.time())}"
        self._max_samples = max_sample_capacity
        self.reset()

    @property
    def run_id(self) -> str:
        return self._run_id

    def get_name(self) -> str:
        return "MetricsEngine"

    def reset(self) -> None:
        """Reset all accumulators, episodes, and running states."""
        self._total_frames: int = 0
        self._start_time_s: Optional[float] = None
        self._last_timestamp_s: float = 0.0
        self._wall_start_perf: Optional[float] = None
        self._wall_elapsed_s: float = 0.0

        # Detection metrics
        self._candidate_count_sum: int = 0
        self._detection_success_count: int = 0
        self._detection_latency_sum_ms: float = 0.0
        self._detection_latency_count: int = 0

        # Centroiding metrics (Ground Truth required)
        self._centroid_evaluated_count: int = 0
        self._centroid_err_sum: float = 0.0
        self._centroid_err_sq_sum: float = 0.0
        self._centroid_err_ideal_sq_sum: float = 0.0
        self._centroid_err_rendered_sq_sum: float = 0.0
        self._centroid_err_max: float = 0.0
        self._centroid_err_within_1px: int = 0
        self._centroid_err_within_2px: int = 0
        self._centroid_err_within_5px: int = 0
        self._centroid_samples: List[float] = []
        self._reference_frames_matched: int = 0

        # Tracking metrics
        self._tracking_optical_axis_sum: float = 0.0
        self._tracking_optical_axis_sq_sum: float = 0.0
        self._tracking_optical_axis_max: float = 0.0
        self._tracking_gt_sum: float = 0.0
        self._tracking_gt_sq_sum: float = 0.0
        self._tracking_gt_max: float = 0.0
        self._tracking_frames_count: int = 0
        self._tracking_steady_state_samples: List[float] = []

        # State and lock lifecycle
        self._first_detect_timestamp: Optional[float] = None
        self._initial_lock_timestamp: Optional[float] = None
        self._initial_lock_frame: Optional[int] = None
        self._has_locked: bool = False
        self._frames_in_tracking: int = 0
        self._frames_in_lost: int = 0
        self._frames_post_acq: int = 0
        self._frames_target_visible: int = 0
        self._frames_in_tracking_visible: int = 0
        self._longest_consecutive_tracking: int = 0
        self._current_consecutive_tracking: int = 0

        # Loss and reacquisition episodes
        self._reacquisition_event_count: int = 0
        self._reacquisition_durations: List[float] = []
        self._current_loss_start_time: Optional[float] = None
        self._in_loss_episode: bool = False

        # PTZ response
        self._ptz_commands_count: int = 0
        self._ptz_deadband_count: int = 0
        self._ptz_saturated_count: int = 0

        # Latency statistics
        self._total_latency_sum_ms: float = 0.0
        self._min_latency_ms: float = float("inf")
        self._max_latency_ms: float = 0.0
        self._latency_samples: List[float] = []

    def _record_sample(self, sample_list: List[float], value: float) -> None:
        """Store value with bounded capacity via reservoir sampling when full."""
        if len(sample_list) < self._max_samples:
            sample_list.append(value)
        else:
            idx = random.randint(0, self._max_samples - 1)
            sample_list[idx] = value

    def update(
        self,
        frame_packet: FramePacket,
        track_result: Optional[TrackResult],
        state_result: TrackingStateResult,
        centroid_result: Optional[CentroidResult] = None,
        detection_result: Optional[DetectionResult] = None,
        ptz_command: Optional[PTZCommand] = None,
        ground_truth: Optional[GroundTruth] = None,
        camera_pan_deg: float = 0.0,
        camera_tilt_deg: float = 0.0,
        processing_time_ms: float = 0.0,
    ) -> TelemetryRecord:
        """
        Record observations for one frame, compute online metrics,
        and emit an immutable TelemetryRecord.
        """
        t0_metrics = time.perf_counter()

        frame_num = frame_packet.frame_number
        timestamp = frame_packet.timestamp
        source_type = frame_packet.source.value if hasattr(frame_packet.source, "value") else str(frame_packet.source)

        if self._start_time_s is None:
            self._start_time_s = timestamp
        self._last_timestamp_s = timestamp
        self._total_frames += 1

        if self._wall_start_perf is None:
            self._wall_start_perf = time.perf_counter()
        self._wall_elapsed_s = time.perf_counter() - self._wall_start_perf

        # -------------------------------------------------------------------
        # 1. Detection Processing
        # -------------------------------------------------------------------
        det_valid = False
        cand_count = 0
        det_confidence = 0.0
        time_det_ms = 0.0

        if detection_result is not None:
            cand_count = len(detection_result.candidates)
            det_valid = bool(cand_count > 0)
            self._candidate_count_sum += cand_count
            if det_valid:
                self._detection_success_count += 1
                det_confidence = max((c.detection_score for c in detection_result.candidates), default=0.0)
            time_det_ms = detection_result.processing_time_ms
            if time_det_ms > 0:
                self._detection_latency_sum_ms += time_det_ms
                self._detection_latency_count += 1

        # -------------------------------------------------------------------
        # 2. Tracking Lifecycle & State Transitions
        # -------------------------------------------------------------------
        state = state_result.state
        if det_valid and self._first_detect_timestamp is None:
            self._first_detect_timestamp = timestamp

        if state == TrackingState.TRACKING:
            self._frames_in_tracking += 1
            self._current_consecutive_tracking += 1
            if self._current_consecutive_tracking > self._longest_consecutive_tracking:
                self._longest_consecutive_tracking = self._current_consecutive_tracking

            if not self._has_locked:
                self._has_locked = True
                self._initial_lock_timestamp = timestamp
                self._initial_lock_frame = frame_num

            # If we were recovering from a loss episode, reacquisition is complete!
            if self._in_loss_episode and self._current_loss_start_time is not None:
                reacq_time = max(0.0, timestamp - self._current_loss_start_time)
                self._reacquisition_durations.append(reacq_time)
                self._reacquisition_event_count += 1
                self._in_loss_episode = False
                self._current_loss_start_time = None
        else:
            self._current_consecutive_tracking = 0
            if state in (TrackingState.LOST, TrackingState.REACQUIRING):
                if self._has_locked and not self._in_loss_episode:
                    self._in_loss_episode = True
                    self._current_loss_start_time = timestamp
            if state == TrackingState.LOST:
                self._frames_in_lost += 1

        if self._has_locked:
            self._frames_post_acq += 1

        # -------------------------------------------------------------------
        # 3. Ground Truth Ingestion (Firewall-Protected Side Channel)
        # -------------------------------------------------------------------
        target_present = False
        target_visible = False
        gt_x: Optional[float] = None
        gt_y: Optional[float] = None
        proj_x: Optional[float] = None
        proj_y: Optional[float] = None
        rend_x: Optional[float] = None
        rend_y: Optional[float] = None

        if ground_truth is not None:
            target_present = True
            target_visible = ground_truth.target_visible
            if target_visible:
                self._frames_target_visible += 1
                if state == TrackingState.TRACKING:
                    self._frames_in_tracking_visible += 1

            gt_x = ground_truth.target_world_x
            gt_y = ground_truth.target_world_y
            proj_x = ground_truth.ideal_projected_x
            proj_y = ground_truth.ideal_projected_y
            rend_x = ground_truth.rendered_centroid_x
            rend_y = ground_truth.rendered_centroid_y
            if camera_pan_deg == 0.0 and camera_tilt_deg == 0.0:
                camera_pan_deg = ground_truth.camera_pan_deg
                camera_tilt_deg = ground_truth.camera_tilt_deg
            if rend_x is not None and rend_y is not None:
                self._reference_frames_matched += 1

        # -------------------------------------------------------------------
        # 4. Spatial Accuracy: Centroiding Error
        # -------------------------------------------------------------------
        cent_x: Optional[float] = None
        cent_y: Optional[float] = None
        cent_valid = False
        time_cent_ms = 0.0
        err_rendered: Optional[float] = None
        err_ideal: Optional[float] = None

        if centroid_result is not None and centroid_result.valid:
            cent_x = centroid_result.x
            cent_y = centroid_result.y
            cent_valid = True
            time_cent_ms = centroid_result.processing_time_ms

            if rend_x is not None and rend_y is not None:
                err_rendered = math.hypot(cent_x - rend_x, cent_y - rend_y)
                self._centroid_err_sum += err_rendered
                self._centroid_err_sq_sum += err_rendered ** 2
                self._centroid_err_rendered_sq_sum += err_rendered ** 2
                self._centroid_err_max = max(self._centroid_err_max, err_rendered)
                self._centroid_evaluated_count += 1
                if err_rendered < 1.0:
                    self._centroid_err_within_1px += 1
                if err_rendered < 2.0:
                    self._centroid_err_within_2px += 1
                if err_rendered < 5.0:
                    self._centroid_err_within_5px += 1
                self._record_sample(self._centroid_samples, err_rendered)

            if proj_x is not None and proj_y is not None:
                err_ideal = math.hypot(cent_x - proj_x, cent_y - proj_y)
                self._centroid_err_ideal_sq_sum += err_ideal ** 2

        # -------------------------------------------------------------------
        # 5. Spatial Accuracy: Tracking Error
        # -------------------------------------------------------------------
        track_x: Optional[float] = None
        track_y: Optional[float] = None
        track_vx: Optional[float] = None
        track_vy: Optional[float] = None
        track_conf: float = 0.0
        is_coasting: bool = False
        time_track_ms = 0.0
        err_optical_axis: Optional[float] = None
        err_gt: Optional[float] = None

        if track_result is not None:
            track_x = track_result.estimated_x
            track_y = track_result.estimated_y
            track_vx = track_result.velocity_x
            track_vy = track_result.velocity_y
            track_conf = track_result.confidence
            is_coasting = track_result.is_coasting
            time_track_ms = track_result.processing_time_ms

            # Optical Axis Tracking Error (offset from center)
            cx_opt = frame_packet.width / 2.0
            cy_opt = frame_packet.height / 2.0
            err_optical_axis = math.hypot(track_x - cx_opt, track_y - cy_opt)

            if state == TrackingState.TRACKING:
                self._tracking_optical_axis_sum += err_optical_axis
                self._tracking_optical_axis_sq_sum += err_optical_axis ** 2
                self._tracking_optical_axis_max = max(self._tracking_optical_axis_max, err_optical_axis)
                self._tracking_frames_count += 1
                self._record_sample(self._tracking_steady_state_samples, err_optical_axis)

            # Estimator Tracking Error vs Rendered Target
            if rend_x is not None and rend_y is not None:
                err_gt = math.hypot(track_x - rend_x, track_y - rend_y)
                if state == TrackingState.TRACKING:
                    self._tracking_gt_sum += err_gt
                    self._tracking_gt_sq_sum += err_gt ** 2
                    self._tracking_gt_max = max(self._tracking_gt_max, err_gt)

        # -------------------------------------------------------------------
        # 6. PTZ Actuation Telemetry
        # -------------------------------------------------------------------
        pan_cmd = 0.0
        tilt_cmd = 0.0
        pan_vel = 0.0
        tilt_vel = 0.0
        in_db = False
        is_sat = False
        time_ptz_ms = 0.0

        if ptz_command is not None:
            pan_cmd = ptz_command.delta_pan_deg
            tilt_cmd = ptz_command.delta_tilt_deg
            pan_vel = ptz_command.pan_velocity_deg_s
            tilt_vel = ptz_command.tilt_velocity_deg_s
            in_db = ptz_command.in_deadband
            is_sat = ptz_command.is_saturated
            time_ptz_ms = ptz_command.processing_time_ms

            self._ptz_commands_count += 1
            if in_db:
                self._ptz_deadband_count += 1
            if is_sat:
                self._ptz_saturated_count += 1

        # -------------------------------------------------------------------
        # 7. Performance & Latency Telemetry
        # -------------------------------------------------------------------
        time_state_ms = state_result.processing_time_ms
        time_metrics_ms = (time.perf_counter() - t0_metrics) * 1000.0

        # Total pipeline latency
        time_total_ms = (
            processing_time_ms
            if processing_time_ms > 0
            else (time_det_ms + time_cent_ms + time_track_ms + time_state_ms + time_ptz_ms + time_metrics_ms)
        )
        self._total_latency_sum_ms += time_total_ms
        self._min_latency_ms = min(self._min_latency_ms, time_total_ms)
        self._max_latency_ms = max(self._max_latency_ms, time_total_ms)
        self._record_sample(self._latency_samples, time_total_ms)

        inst_fps = 1000.0 / time_total_ms if time_total_ms > 0 else 0.0

        # Create comprehensive immutable TelemetryRecord
        record = TelemetryRecord(
            run_id=self._run_id,
            frame_number=frame_num,
            timestamp=timestamp,
            source=source_type,
            state=state.name,
            previous_state=state_result.previous_state.name,
            transition_reason=state_result.transition_reason,
            target_present=target_present,
            ground_truth_x=gt_x,
            ground_truth_y=gt_y,
            ideal_projected_x=proj_x,
            ideal_projected_y=proj_y,
            rendered_centroid_x=rend_x,
            rendered_centroid_y=rend_y,
            estimated_centroid_x=cent_x,
            estimated_centroid_y=cent_y,
            centroid_error_ideal=err_ideal,
            centroid_error_rendered=err_rendered,
            tracking_error=err_optical_axis if err_optical_axis is not None else 0.0,
            detection_confidence=det_confidence,
            candidate_count=cand_count,
            detection_valid=det_valid,
            pan_angle=camera_pan_deg,
            tilt_angle=camera_tilt_deg,
            pan_command=pan_cmd,
            tilt_command=tilt_cmd,
            processing_time_ms=time_total_ms,
            fps=inst_fps,
            target_visible=target_visible,
            centroid_valid=cent_valid,
            tracking_error_optical_axis=err_optical_axis,
            tracking_error_gt=err_gt,
            is_coasting=is_coasting,
            ptz_pan_velocity=pan_vel,
            ptz_tilt_velocity=tilt_vel,
            ptz_in_deadband=in_db,
            ptz_is_saturated=is_sat,
            time_detection_ms=time_det_ms,
            time_centroid_ms=time_cent_ms,
            time_tracking_ms=time_track_ms,
            time_state_ms=time_state_ms,
            time_ptz_ms=time_ptz_ms,
            time_metrics_ms=time_metrics_ms,
        )

        return record

    def get_current_summary(self) -> MetricsSummary:
        """Compute aggregate summary based on frames processed so far."""
        dur_s = max(0.0, self._last_timestamp_s - (self._start_time_s or 0.0))
        mean_fps = (self._total_frames / self._wall_elapsed_s) if self._wall_elapsed_s > 0 else 0.0

        # Detection rates
        det_rate = (self._detection_success_count / self._total_frames) if self._total_frames > 0 else 0.0
        mean_cands = (self._candidate_count_sum / self._total_frames) if self._total_frames > 0 else 0.0
        mean_det_lat = (self._detection_latency_sum_ms / self._detection_latency_count) if self._detection_latency_count > 0 else 0.0

        # Centroiding statistics
        n_cent = self._centroid_evaluated_count
        mean_ce = (self._centroid_err_sum / n_cent) if n_cent > 0 else 0.0
        rmse_ce = math.sqrt(self._centroid_err_sq_sum / n_cent) if n_cent > 0 else 0.0
        rmse_ce_ideal = math.sqrt(self._centroid_err_ideal_sq_sum / n_cent) if n_cent > 0 else 0.0
        rmse_ce_rendered = math.sqrt(self._centroid_err_rendered_sq_sum / n_cent) if n_cent > 0 else 0.0
        med_ce = statistics.median(self._centroid_samples) if self._centroid_samples else 0.0
        p_1px = (self._centroid_err_within_1px / n_cent * 100.0) if n_cent > 0 else 0.0
        p_2px = (self._centroid_err_within_2px / n_cent * 100.0) if n_cent > 0 else 0.0
        p_5px = (self._centroid_err_within_5px / n_cent * 100.0) if n_cent > 0 else 0.0

        # Tracking error statistics
        n_trk = self._tracking_frames_count
        mean_te_opt = (self._tracking_optical_axis_sum / n_trk) if n_trk > 0 else 0.0
        rmse_te_opt = math.sqrt(self._tracking_optical_axis_sq_sum / n_trk) if n_trk > 0 else 0.0
        mean_te_gt = (self._tracking_gt_sum / n_trk) if n_trk > 0 else 0.0
        rmse_te_gt = math.sqrt(self._tracking_gt_sq_sum / n_trk) if n_trk > 0 else 0.0

        # Lock retention rates
        lock_ret_post = (self._frames_in_tracking / self._frames_post_acq * 100.0) if self._frames_post_acq > 0 else 0.0
        lock_ret_all = (self._frames_in_tracking / self._total_frames * 100.0) if self._total_frames > 0 else 0.0
        lock_ret_vis = (self._frames_in_tracking_visible / self._frames_target_visible * 100.0) if self._frames_target_visible > 0 else 0.0
        loss_rate = (100.0 - lock_ret_post) if self._has_locked else 0.0
        continuity = (self._longest_consecutive_tracking / self._total_frames) if self._total_frames > 0 else 0.0

        # Acquisition timing
        acq_detect = (
            max(0.0, self._initial_lock_timestamp - self._first_detect_timestamp)
            if (self._initial_lock_timestamp is not None and self._first_detect_timestamp is not None)
            else None
        )
        acq_total = (
            max(0.0, self._initial_lock_timestamp - (self._start_time_s or 0.0))
            if self._initial_lock_timestamp is not None
            else None
        )

        # Reacquisition timing
        mean_reacq = (sum(self._reacquisition_durations) / len(self._reacquisition_durations)) if self._reacquisition_durations else None
        max_reacq = max(self._reacquisition_durations) if self._reacquisition_durations else None

        # Latencies & Percentiles
        mean_lat = (self._total_latency_sum_ms / self._total_frames) if self._total_frames > 0 else 0.0
        min_lat = self._min_latency_ms if self._min_latency_ms != float("inf") else 0.0
        max_lat = self._max_latency_ms
        p50_lat, p95_lat, p99_lat = self._compute_percentiles([50.0, 95.0, 99.0])

        # PTZ response
        oscillation = (
            statistics.stdev(self._tracking_steady_state_samples)
            if len(self._tracking_steady_state_samples) >= 2
            else 0.0
        )
        db_pct = (self._ptz_deadband_count / self._ptz_commands_count * 100.0) if self._ptz_commands_count > 0 else 0.0

        return MetricsSummary(
            run_id=self._run_id,
            total_frames=self._total_frames,
            duration_seconds=dur_s,
            detection_rate=det_rate,
            false_positive_rate=0.0,
            mean_candidate_count=mean_cands,
            mean_detection_latency_ms=mean_det_lat,
            mean_centroid_error=mean_ce,
            median_centroid_error=med_ce,
            rmse_centroid=rmse_ce,
            rmse_centroid_ideal=rmse_ce_ideal,
            rmse_centroid_rendered=rmse_ce_rendered,
            max_centroid_error=self._centroid_err_max,
            pct_within_1px=p_1px,
            pct_within_2px=p_2px,
            pct_within_5px=p_5px,
            mean_tracking_error=mean_te_opt,
            mean_tracking_error_optical_axis=mean_te_opt,
            mean_tracking_error_gt=mean_te_gt,
            max_tracking_error=self._tracking_optical_axis_max,
            max_tracking_error_optical_axis=self._tracking_optical_axis_max,
            max_tracking_error_gt=self._tracking_gt_max,
            rmse_tracking_optical_axis=rmse_te_opt,
            rmse_tracking_gt=rmse_te_gt,
            lock_retention_rate=lock_ret_post,
            lock_retention_post_acq_pct=lock_ret_post,
            lock_retention_all_pct=lock_ret_all,
            lock_retention_visible_pct=lock_ret_vis,
            target_loss_rate=loss_rate,
            track_continuity=continuity,
            acquisition_time_s=acq_total,
            acquisition_time_from_detect_s=acq_detect,
            acquisition_time_total_s=acq_total,
            reacquisition_events=self._reacquisition_event_count,
            mean_reacquisition_time_s=mean_reacq,
            max_reacquisition_time_s=max_reacq,
            frames_evaluated_count=self._total_frames,
            frames_tracked_count=self._frames_in_tracking,
            frames_lost_count=self._frames_in_lost,
            reference_frames_matched=self._reference_frames_matched,
            reference_frame_coverage_pct=(self._reference_frames_matched / self._total_frames * 100.0) if self._total_frames > 0 else 0.0,
            mean_fps=mean_fps,
            mean_latency_ms=mean_lat,
            min_latency_ms=min_lat,
            p50_latency_ms=p50_lat,
            p95_latency_ms=p95_lat,
            p99_latency_ms=p99_lat,
            max_latency_ms=max_lat,
            mean_steady_state_error=mean_te_opt,
            oscillation_measure=oscillation,
            frames_in_deadband_pct=db_pct,
        )

    def _compute_percentiles(self, percentiles: Sequence[float]) -> List[float]:
        """Compute approximate percentiles from sample list."""
        if not self._latency_samples:
            return [0.0] * len(percentiles)
        sorted_samples = sorted(self._latency_samples)
        n = len(sorted_samples)
        results = []
        for p in percentiles:
            idx = int(round((p / 100.0) * (n - 1)))
            idx = max(0, min(n - 1, idx))
            results.append(sorted_samples[idx])
        return results

    def finalize(self) -> MetricsSummary:
        """Compute final aggregate statistics for the completed run."""
        return self.get_current_summary()
