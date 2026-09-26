"""
Unit tests for Local Contrast Clutter disturbance (Stage 4.5 in DisturbanceEngine).

Tests:
  1. LocalContrastConfig dataclass defaults and parameters.
  2. apply_local_contrast_clutter disabled leaves frame identical.
  3. apply_local_contrast_clutter enabled produces spatially-varying additive perturbation.
  4. Seed determinism: identical seed produces identical perturbation.
  5. Amplitude control: higher amplitude increases perturbation variance.
  6. Margin validation: beacon peak intensity vs clutter amplitude constraint.
"""

from __future__ import annotations
import numpy as np
import pytest

from src.config.config_manager import LocalContrastConfig, ConfigManager, TargetConfig
from src.simulation.disturbance_engine import DisturbanceEngine


class TestLocalContrastDisturbance:
    def test_local_contrast_config_defaults(self):
        cfg = LocalContrastConfig()
        assert cfg.enabled is False
        assert cfg.amplitude > 0.0
        assert cfg.spatial_scale > 0.0
        assert cfg.num_blobs > 0

    def test_disabled_contrast_leaves_frame_identical(self):
        engine = DisturbanceEngine(
            local_contrast_cfg=LocalContrastConfig(enabled=False),
            seed=42,
        )
        frame = np.full((120, 160), 30, dtype=np.uint8)
        out = engine.apply_local_contrast_clutter(frame)
        np.testing.assert_array_equal(out, frame)

    def test_enabled_contrast_adds_clutter_without_altering_dtype(self):
        engine = DisturbanceEngine(
            local_contrast_cfg=LocalContrastConfig(
                enabled=True,
                amplitude=40.0,
                spatial_scale=50.0,
                num_blobs=4,
            ),
            seed=123,
        )
        frame = np.full((100, 100), 20, dtype=np.uint8)
        out = engine.apply_local_contrast_clutter(frame)

        assert out.dtype == np.uint8
        assert out.shape == frame.shape
        # Some pixels must be perturbed upwards
        assert np.max(out) > 20
        # Perturbation is additive (>= original background)
        assert np.min(out) >= 20

    def test_seed_determinism(self):
        cfg = LocalContrastConfig(enabled=True, amplitude=50.0, spatial_scale=40.0, num_blobs=5)
        e1 = DisturbanceEngine(local_contrast_cfg=cfg, seed=999)
        e2 = DisturbanceEngine(local_contrast_cfg=cfg, seed=999)
        e3 = DisturbanceEngine(local_contrast_cfg=cfg, seed=111)

        frame = np.full((80, 80), 15, dtype=np.uint8)
        out1 = e1.apply_local_contrast_clutter(frame)
        out2 = e2.apply_local_contrast_clutter(frame)
        out3 = e3.apply_local_contrast_clutter(frame)

        np.testing.assert_array_equal(out1, out2)
        assert not np.array_equal(out1, out3)

    def test_amplitude_scaling(self):
        frame = np.full((100, 100), 20, dtype=np.uint8)
        cfg_low = LocalContrastConfig(enabled=True, amplitude=15.0, spatial_scale=30.0)
        cfg_high = LocalContrastConfig(enabled=True, amplitude=75.0, spatial_scale=30.0)

        e_low = DisturbanceEngine(local_contrast_cfg=cfg_low, seed=42)
        e_high = DisturbanceEngine(local_contrast_cfg=cfg_high, seed=42)

        out_low = e_low.apply_local_contrast_clutter(frame)
        out_high = e_high.apply_local_contrast_clutter(frame)

        assert np.max(out_high) > np.max(out_low)

    def test_beacon_peak_margin_validation(self):
        """Beacon peak must exceed local clutter amplitude by min_beacon_margin."""
        cm = ConfigManager()
        cm.config.local_contrast.enabled = True
        cm.config.local_contrast.amplitude = 120.0
        cm.config.local_contrast.min_beacon_margin = 30.0
        # Target intensity 130 -> 130 - 120 = 10 < 30 margin -> should produce validation warning/error
        cm.config.target.intensity = 130

        errors = cm.validate()
        assert any("Local contrast amplitude" in err or "Beacon peak" in err for err in errors)
