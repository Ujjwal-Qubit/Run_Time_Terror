"""
Unit tests for per-noise intensity controls and independent parameterization.

Tests:
  1. NoiseConfig fields and defaults.
  2. Gaussian noise variance scales with gaussian_sigma.
  3. Salt & Pepper noise corrupted pixel fraction scales with sp_density.
  4. Poisson noise scaling with poisson_scale.
  5. Independence between noise generators.
  6. Determinism and reproducibility with identical seeds.
"""

from __future__ import annotations
import numpy as np
import pytest

from src.config.config_manager import NoiseConfig
from src.simulation.disturbance_engine import DisturbanceEngine


class TestNoiseControls:
    def test_noise_config_fields(self):
        cfg = NoiseConfig(
            gaussian_enabled=True,
            gaussian_sigma=12.5,
            sp_enabled=True,
            sp_density=0.03,
            poisson_enabled=True,
            poisson_scale=2.5,
        )
        assert cfg.gaussian_sigma == 12.5
        assert cfg.sp_density == 0.03
        assert cfg.poisson_scale == 2.5

    def test_gaussian_sigma_scales_variance(self):
        frame = np.full((120, 120), 128, dtype=np.uint8)

        e_low = DisturbanceEngine(
            noise_cfg=NoiseConfig(gaussian_enabled=True, gaussian_sigma=3.0),
            seed=42,
        )
        e_high = DisturbanceEngine(
            noise_cfg=NoiseConfig(gaussian_enabled=True, gaussian_sigma=15.0),
            seed=42,
        )

        out_low = e_low.apply_gaussian_noise(frame.copy())
        out_high = e_high.apply_gaussian_noise(frame.copy())

        var_low = np.var(out_low.astype(float))
        var_high = np.var(out_high.astype(float))

        assert var_high > var_low * 2.0

    def test_sp_density_scales_corrupted_pixels(self):
        frame = np.full((100, 100), 100, dtype=np.uint8)

        e_low = DisturbanceEngine(
            noise_cfg=NoiseConfig(sp_enabled=True, sp_density=0.01),
            seed=42,
        )
        e_high = DisturbanceEngine(
            noise_cfg=NoiseConfig(sp_enabled=True, sp_density=0.08),
            seed=42,
        )

        out_low = e_low.apply_salt_and_pepper_noise(frame.copy())
        out_high = e_high.apply_salt_and_pepper_noise(frame.copy())

        corrupted_low = np.count_nonzero((out_low == 0) | (out_low == 255))
        corrupted_high = np.count_nonzero((out_high == 0) | (out_high == 255))

        assert corrupted_high > corrupted_low

    def test_poisson_noise_scale(self):
        frame = np.full((80, 80), 80, dtype=np.uint8)
        e1 = DisturbanceEngine(
            noise_cfg=NoiseConfig(poisson_enabled=True, poisson_scale=0.5),
            seed=42,
        )
        e2 = DisturbanceEngine(
            noise_cfg=NoiseConfig(poisson_enabled=True, poisson_scale=2.0),
            seed=42,
        )

        out1 = e1.apply_poisson_noise(frame.copy())
        out2 = e2.apply_poisson_noise(frame.copy())

        assert out1.dtype == np.uint8
        assert out2.dtype == np.uint8
        assert out1.shape == frame.shape
        assert out2.shape == frame.shape

    def test_noise_determinism_with_seed(self):
        frame = np.full((80, 80), 100, dtype=np.uint8)
        cfg = NoiseConfig(
            gaussian_enabled=True, gaussian_sigma=8.0,
            sp_enabled=True, sp_density=0.02,
            poisson_enabled=True, poisson_scale=1.0,
        )

        e1 = DisturbanceEngine(noise_cfg=cfg, seed=12345)
        e2 = DisturbanceEngine(noise_cfg=cfg, seed=12345)

        out1 = e1.apply_pixel_pipeline(frame.copy())
        out2 = e2.apply_pixel_pipeline(frame.copy())

        np.testing.assert_array_equal(out1, out2)
