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
                    sm = SceneManager(cfg.scene)
                    tm = TargetManager(cfg.target, cfg.motion, seed=seed + scenario_count)
                    cam = CameraModel(cfg.camera)
                    de = DisturbanceEngine(cfg.platform_motion, cfg.jitter, cfg.atmospheric, cfg.noise, seed=seed)
                    gt_prov = GroundTruthProvider()
                    detector = P0ThresholdDetector(cfg.detector)

                    for frame_idx in range(frames_per_scenario):
                        t = frame_idx * (1.0 / 30.0)
                        target_state = tm.step(1.0 / 30.0)
                        eff_cx, eff_cy = de.apply_geometric_disturbances(cam.world_position[0], cam.world_position[1], 1.0 / 30.0)
                        canvas = sm.render(target_state.world_x, target_state.world_y, target_state.patch)
                        clean_vp = cam.extract_viewport(canvas, eff_cx, eff_cy)
                        gt = gt_prov.capture(frame_idx, t, target_state, cam, clean_vp, eff_cx, eff_cy)
                        dist_frame = de.apply_pixel_pipeline(clean_vp)

                        # FramePacket mock
                        from src.frame.data_contracts import FramePacket, FrameSource
                        packet = FramePacket(
                            frame_number=frame_idx,
                            timestamp=t,
                            image=dist_frame,
                            width=cfg.camera.width,
                            height=cfg.camera.height,
                            source=FrameSource.SIMULATION,
                        )

                        det_res = detector.detect(packet)
                        for cand_idx, cand in enumerate(det_res.candidates):
                            fv = extractor.extract(packet, cand, candidate_id=cand_idx)

                            # Label ground truth overlap
                            gt_x = gt.rendered_centroid_x
                            gt_y = gt.rendered_centroid_y
                            is_beacon = 0
                            if gt_x is not None and gt_y is not None and gt.target_visible:
                                cand_x = getattr(cand, "centroid_x", cand.bbox_x + cand.bbox_w / 2.0)
                                cand_y = getattr(cand, "centroid_y", cand.bbox_y + cand.bbox_h / 2.0)
                                dist = math.hypot(cand_x - gt_x, cand_y - gt_y)
                                if dist <= max(10.0, size * 1.5):
                                    is_beacon = 1


                            feat_dict = dict(zip(fv.feature_names, fv.values))
                            rec = CandidateDatasetRecord(
                                dataset_version="candidate-v1",
                                run_id=run_id,
                                frame_number=frame_idx,
                                candidate_id=cand_idx,
                                features=feat_dict,
                                label=is_beacon,
                                label_definition="candidate overlaps rendered beacon region" if is_beacon else "noise candidate",
                            )
                            records.append(rec.to_dict())

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
