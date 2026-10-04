"""
Dataset Generator CLI — Generates labeled candidate and temporal sequence datasets
from simulation runs per Spec §8 & Runbook §3.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any, Dict, List
import numpy as np

from src.aiml.feature_extractor import CandidateFeatureExtractor
from src.config.config_manager import ConfigManager
from src.data.dataset_manifest import DatasetManifest
from src.data.dataset_schema import CandidateDatasetRecord, TemporalSequenceRecord
from src.data.split_builder import SplitBuilder
from src.simulation.camera_model import CameraModel
from src.simulation.disturbance_engine import DisturbanceEngine
from src.simulation.ground_truth_provider import GroundTruthProvider
from src.simulation.scene_manager import SceneManager
from src.simulation.target_manager import TargetManager
from src.tracker.detection_engine import P0ThresholdDetector


class SyntheticDatasetGenerator:
    """
    Generates synthetic candidate and temporal datasets.
    """

    def __init__(self, output_dir: str = "datasets/processed/candidate-v1") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_candidate_dataset(
        self,
        num_scenarios: int = 10,
        frames_per_scenario: int = 100,
        seed: int = 42,
    ) -> str:
        """
        Generate candidate classification dataset.
        """
        motion_types = ["STRAIGHT_LINE", "CIRCULAR", "FIGURE_8", "RANDOM"]
        target_sizes = [5, 10, 20]
        atmos_conditions = ["CLEAR", "HAZE", "FOG"]

        extractor = CandidateFeatureExtractor()
        records: List[Dict[str, Any]] = []

        scenario_count = 0
        rng = np.random.RandomState(seed)

        for m_type in motion_types:
            for size in target_sizes:
                for atmos in atmos_conditions:
                    if scenario_count >= num_scenarios:
                        break

                    run_id = f"sim_seed_{seed}_m_{m_type}_s_{size}_a_{atmos}"
                    cm = ConfigManager()
                    cm.update_section("motion", motion_type=m_type)
                    cm.update_section("target", size=size, initial_position="center", initial_x=1000.0, initial_y=1000.0)
                    cm.update_section("atmospheric", condition=atmos)

                    cfg = cm.config

                    # Configure realistic distractors and clutter
                    from src.config.config_manager import BeaconConfig
                    # Include secondary distractor in 75% of scenarios
                    has_secondary = (scenario_count % 4 != 0)
                    beacon_list = [
                        BeaconConfig(
                            beacon_id="primary",
                            role="primary",
                            size=size,
                            intensity=220,
                            x=1000.0,
                            y=1000.0,
                            speed=15.0,
                        )
                    ]
                    if has_secondary:
                        beacon_list.append(
                            BeaconConfig(
                                beacon_id="distractor",
                                role="secondary",
                                size=max(5, size - 3),
                                intensity=155,
                                x=1050.0 + float(rng.uniform(-50, 50)),
                                y=1030.0 + float(rng.uniform(-50, 50)),
                                speed=10.0,
                            )
                        )

                    # Enable local contrast background clutter in 75% of scenarios
                    has_clutter = (scenario_count % 4 != 1)
                    cfg.local_contrast.enabled = has_clutter
                    cfg.local_contrast.amplitude = float(rng.uniform(25.0, 42.0))
                    cfg.local_contrast.num_blobs = int(rng.randint(6, 12))
                    cfg.local_contrast.spatial_scale = 5.0

                    # Enable sensor noise
                    cfg.noise.gaussian_enabled = True
                    cfg.noise.gaussian_sigma = float(rng.uniform(4.0, 10.0))
                    cfg.noise.poisson_enabled = True

                    sm = SceneManager(cfg.scene)
                    from src.simulation.target_manager import MultiBeaconManager
                    mbm = MultiBeaconManager(
                        beacon_configs=beacon_list,
                        motion_config=cfg.motion,
                        scene_width=cfg.scene.width,
                        scene_height=cfg.scene.height,
                        seed=seed + scenario_count,
                    )
                    tm = mbm._primary_manager
                    cam = CameraModel(cfg.camera, scene_width=cfg.scene.width, scene_height=cfg.scene.height)
                    de = DisturbanceEngine(
                        platform_cfg=cfg.platform_motion,
                        jitter_cfg=cfg.jitter,
                        atmos_cfg=cfg.atmospheric,
                        noise_cfg=cfg.noise,
                        local_contrast_cfg=cfg.local_contrast,
                        seed=seed + scenario_count,
                    )
                    gt_prov = GroundTruthProvider()
                    detector = P0ThresholdDetector(cfg.detector)

                    from src.frame.simulation_provider import SimulationFrameProvider
                    provider = SimulationFrameProvider(
                        scene_manager=sm,
                        target_manager=tm,
                        camera_model=cam,
                        disturbance_engine=de,
                        ground_truth_provider=gt_prov,
                        fps=30,
                        max_duration_s=float(frames_per_scenario) / 30.0 + 0.1,
                        multi_beacon_manager=mbm,
                    )

                    # Causal Kalman tracker for genuine temporal feature generation
                    from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker
                    from src.frame.data_contracts import CentroidResult
                    tracker = ConstantVelocityKalmanTracker()
                    prev_pos = None

                    scenario_pos: List[Dict[str, Any]] = []
                    scenario_neg: List[Dict[str, Any]] = []

                    for frame_idx in range(frames_per_scenario):
                        packet = provider.get_next_frame()
                        if packet is None:
                            break

                        pred_pos = tracker.predict() if tracker.is_initialized else None
                        det_res = detector.detect(packet)
                        gt = gt_prov.get_truth(packet.frame_number)

                        best_meas = None
                        for cand_idx, cand in enumerate(det_res.candidates):
                            # Causal feature extraction (no future or GT info)
                            fv = extractor.extract(
                                packet,
                                cand,
                                predicted_position=pred_pos,
                                previous_position=prev_pos,
                                candidate_id=cand_idx,
                            )

                            cand_x = getattr(cand, "raw_centroid_x", cand.bbox_x + cand.bbox_w / 2.0)
                            cand_y = getattr(cand, "raw_centroid_y", cand.bbox_y + cand.bbox_h / 2.0)

                            # Ground truth overlap check with primary beacon only
                            is_beacon = 0
                            if gt is not None and gt.target_visible and gt.rendered_centroid_x is not None:
                                dist = math.hypot(cand_x - gt.rendered_centroid_x, cand_y - gt.rendered_centroid_y)
                                if dist <= max(10.0, size * 1.5):
                                    is_beacon = 1
                                    if best_meas is None:
                                        best_meas = CentroidResult(
                                            x=cand_x,
                                            y=cand_y,
                                            valid=True,
                                            frame_number=frame_idx,
                                            timestamp=packet.timestamp,
                                        )

                            feat_dict = dict(zip(fv.feature_names, fv.values))
                            rec = CandidateDatasetRecord(
                                dataset_version="candidate-v1",
                                run_id=run_id,
                                frame_number=frame_idx,
                                candidate_id=cand_idx,
                                features=feat_dict,
                                label=is_beacon,
                                label_definition="candidate overlaps primary beacon region" if is_beacon else "clutter / distractor / noise candidate",
                            ).to_dict()

                            if is_beacon == 1:
                                scenario_pos.append(rec)
                            else:
                                scenario_neg.append(rec)

                        # Advance tracker causally
                        if best_meas is not None:
                            tracker.update(best_meas, dt=1.0/30.0, frame_number=frame_idx, timestamp=packet.timestamp)
                            prev_pos = (best_meas.x, best_meas.y)
                        elif tracker.is_initialized:
                            tracker.update(None, dt=1.0/30.0, frame_number=frame_idx, timestamp=packet.timestamp)

                    # Balanced sampling within scenario: keep all positives, sample balanced negatives
                    records.extend(scenario_pos)
                    if scenario_neg:
                        max_negs = max(len(scenario_pos), int(len(scenario_pos) * 1.25))
                        if len(scenario_neg) > max_negs:
                            neg_indices = rng.choice(len(scenario_neg), size=max_negs, replace=False)
                            sampled_negs = [scenario_neg[i] for i in neg_indices]
                            records.extend(sampled_negs)
                        else:
                            records.extend(scenario_neg)

                    scenario_count += 1

        # Build train / val / test splits
        train, val, test = SplitBuilder.build_split(records, group_key="run_id", seed=seed)
        SplitBuilder.save_splits(self.output_dir, train, val, test)

        manifest = DatasetManifest(dataset_name="candidate-v1", task="candidate_classification", seed=seed)
        manifest_path = manifest.save(self.output_dir, len(records), list(set(r["run_id"] for r in records)))
        return manifest_path

    def generate_temporal_dataset(
        self,
        num_scenarios: int = 10,
        frames_per_scenario: int = 100,
        history_lengths: List[int] | None = None,
        seed: int = 42,
    ) -> str:
        """
        Generate temporal sequence dataset for training/evaluating motion predictors.
        """
        history_lengths = history_lengths or [3, 5, 8, 12, 20]
        if not history_lengths or any(length < 2 for length in history_lengths):
            raise ValueError("history_lengths must contain integers of at least 2 for velocity features")

        motion_types = ["STRAIGHT_LINE", "CIRCULAR", "FIGURE_8", "RANDOM"]
        target_sizes = [5, 10, 20]
        records: List[Dict[str, Any]] = []

        scenario_count = 0
        max_h = max(history_lengths)

        for m_type in motion_types:
            for size in target_sizes:
                if scenario_count >= num_scenarios:
                    break

                sequence_id = f"sim_seed_{seed}_m_{m_type}_s_{size}"
                cm = ConfigManager()
                cm.update_section("motion", motion_type=m_type)
                cm.update_section("target", size=size, initial_position="center", initial_x=1000.0, initial_y=1000.0)

                cfg = cm.config
                sm = SceneManager(cfg.scene)
                tm = TargetManager(cfg.target, cfg.motion, seed=seed + scenario_count)
                cam = CameraModel(cfg.camera)
                de = DisturbanceEngine(cfg.platform_motion, cfg.jitter, cfg.atmospheric, cfg.noise, seed=seed)
                gt_prov = GroundTruthProvider()

                history_buf: List[Dict[str, Any]] = []

                for frame_idx in range(frames_per_scenario):
                    t = frame_idx * (1.0 / 30.0)
                    target_state = tm.step(1.0 / 30.0)
                    eff_cx, eff_cy = de.apply_geometric_disturbances(cam.world_position[0], cam.world_position[1], 1.0 / 30.0)
                    canvas = sm.render(target_state.world_x, target_state.world_y, target_state.patch)
                    clean_vp = cam.extract_viewport(canvas, eff_cx, eff_cy)
                    gt = gt_prov.capture(frame_idx, t, target_state, cam, clean_vp, eff_cx, eff_cy)

                    obs = {
                        "timestamp": round(float(t), 4),
                        "x": round(float(gt.rendered_centroid_x), 2) if gt.rendered_centroid_x is not None else None,
                        "y": round(float(gt.rendered_centroid_y), 2) if gt.rendered_centroid_y is not None else None,
                        "valid": bool(gt.target_visible),
                        "confidence": 1.0 if gt.target_visible else 0.0,
                    }
                    history_buf.append(obs)
                    if len(history_buf) > max_h + 1:
                        history_buf.pop(0)

                    if len(history_buf) >= max_h + 1 and gt.target_visible:
                        next_state = tm.target_state
                        target_data = {
                            "x": round(float(gt.rendered_centroid_x), 2) if gt.rendered_centroid_x is not None else 0.0,
                            "y": round(float(gt.rendered_centroid_y), 2) if gt.rendered_centroid_y is not None else 0.0,
                            "vx": round(float(next_state.vx), 2),
                            "vy": round(float(next_state.vy), 2),
                        }


                        rec = TemporalSequenceRecord(
                            dataset_version="temporal-v1",
                            sequence_id=sequence_id,
                            frame_number=frame_idx,
                            input_history=list(history_buf[:-1]),
                            target=target_data,
                            label_source="rendered_centroid_ground_truth",
                            scenario={
                                "motion_type": m_type,
                                "target_size": size,
                                "seed": seed + scenario_count,
                            },
                        )
                        records.append(rec.to_dict())

                scenario_count += 1

        train, val, test = SplitBuilder.build_split(records, group_key="sequence_id", seed=seed)
        SplitBuilder.save_splits(self.output_dir, train, val, test)

        manifest = DatasetManifest(dataset_name="temporal-v1", task="temporal_prediction", seed=seed)
        manifest_path = manifest.save(self.output_dir, len(records), list(set(r["sequence_id"] for r in records)))
        return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic Dataset Generator")
    parser.add_argument("--task", type=str, default="candidate", choices=["candidate", "temporal"])
    parser.add_argument("--output", type=str, default="datasets/processed/candidate-v1")
    parser.add_argument("--scenarios", type=int, default=5)
    parser.add_argument("--frames-per-scenario", type=int, default=50)
    parser.add_argument("--history-lengths", type=str, default="3,5,8,12,20")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gen = SyntheticDatasetGenerator(output_dir=args.output)
    if args.task == "candidate":
        path = gen.generate_candidate_dataset(
            num_scenarios=args.scenarios,
            frames_per_scenario=args.frames_per_scenario,
            seed=args.seed,
        )
        print(f"[DatasetGenerator] Candidate dataset saved to {args.output} (manifest: {path})")
    else:
        h_lengths = [int(x.strip()) for x in args.history_lengths.split(",") if x.strip()]
        path = gen.generate_temporal_dataset(
            num_scenarios=args.scenarios,
            frames_per_scenario=args.frames_per_scenario,
            history_lengths=h_lengths,
            seed=args.seed,
        )
        print(f"[DatasetGenerator] Temporal dataset saved to {args.output} (manifest: {path})")


if __name__ == "__main__":
    main()
