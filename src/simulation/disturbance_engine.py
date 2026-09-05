"""
Disturbance Engine — Module 7 per Architecture v1.2 §4 and §7.

Applies configurable disturbances in the strict, physically justified sequence:
  1. Platform motion (geometric — shifts camera world position)
  2. Camera jitter (geometric — frame-to-frame random offset)
  [3. Viewport extraction — executed by CameraModel]
  4. Atmospheric degradation (pixel — contrast reduction & brightness shift)
  5. Poisson noise (pixel — signal-dependent shot noise, applied first)
  6. Gaussian noise (pixel — additive electronic/sensor noise)
  7. Salt & Pepper noise (pixel — impulse noise applied last)

Preserves the architectural distinction between:
  - Geometric disturbances (affect camera pose in WCS)
  - Atmospheric degradation (modifies optical signal in IPC)
  - Sensor noise (degrades detector read-out in IPC)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np

from src.config.config_manager import (
    PlatformMotionConfig,
    JitterConfig,
    AtmosphericConfig,
    NoiseConfig,
)
from src.config import defaults
from src.frame.data_contracts import AtmosphericCondition


class DisturbanceEngine:
    """
    DisturbanceEngine (Module 7).

    Responsibilities:
      - Compute geometric platform motion offsets
      - Compute geometric camera jitter offsets
      - Apply atmospheric contrast/brightness degradation
      - Apply Poisson shot noise
      - Apply Gaussian sensor noise
      - Apply Salt & Pepper impulse noise
      - Ensure strict execution ordering per Architecture v1.2 §7.1
      - Guarantee deterministic results given an identical random seed
    """

    def __init__(
        self,
        platform_cfg: PlatformMotionConfig | None = None,
        jitter_cfg: JitterConfig | None = None,
        atmos_cfg: AtmosphericConfig | None = None,
        noise_cfg: NoiseConfig | None = None,
        seed: int = defaults.SIM_DEFAULT_RANDOM_SEED,
    ) -> None:
        self._platform_cfg = platform_cfg or PlatformMotionConfig()
        self._jitter_cfg = jitter_cfg or JitterConfig()
        self._atmos_cfg = atmos_cfg or AtmosphericConfig()
        self._noise_cfg = noise_cfg or NoiseConfig()
        self._seed = seed

        # Validate PS required limits
        if self._platform_cfg.max_px_per_frame > defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME:
            raise ValueError(
                f"Platform motion max ({self._platform_cfg.max_px_per_frame}) exceeds PS limit "
                f"({defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME} px/frame)."
            )
        if self._jitter_cfg.max_px_per_frame > defaults.JITTER_MAX_PX_PER_FRAME:
            raise ValueError(
                f"Jitter max ({self._jitter_cfg.max_px_per_frame}) exceeds PS limit "
                f"({defaults.JITTER_MAX_PX_PER_FRAME} px/frame)."
            )
        if self._noise_cfg.gaussian_sigma > defaults.NOISE_GAUSSIAN_MAX_SIGMA:
            raise ValueError(
                f"Gaussian noise sigma ({self._noise_cfg.gaussian_sigma}) exceeds PS limit "
                f"({defaults.NOISE_GAUSSIAN_MAX_SIGMA})."
            )

        # Independent RNG streams initialized with seed
        self._rng_platform = np.random.RandomState(self._seed + 1)
        self._rng_jitter = np.random.RandomState(self._seed + 2)
        self._rng_noise = np.random.RandomState(self._seed + 3)

        self._time = 0.0
        self._last_platform_offset = (0.0, 0.0)
        self._last_jitter_offset = (0.0, 0.0)

    @property
    def last_platform_offset(self) -> Tuple[float, float]:
        return self._last_platform_offset

    @property
    def last_jitter_offset(self) -> Tuple[float, float]:
        return self._last_jitter_offset

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset all RNG streams and disturbance states."""
        if seed is not None:
            self._seed = seed
        self._rng_platform = np.random.RandomState(self._seed + 1)
        self._rng_jitter = np.random.RandomState(self._seed + 2)
        self._rng_noise = np.random.RandomState(self._seed + 3)
        self._time = 0.0
        self._last_platform_offset = (0.0, 0.0)
        self._last_jitter_offset = (0.0, 0.0)

    # -----------------------------------------------------------------------
    # 1 & 2. Geometric Disturbances (WCS)
    # -----------------------------------------------------------------------

    def compute_platform_motion(self, dt: float) -> Tuple[float, float]:
        """
        Stage 1: Platform Motion (Geometric).
        Computes the platform motion shift for this frame.
        PS Row 25: max +/- 20 px/frame, Linear mandatory.
        """
        if not self._platform_cfg.enabled:
            self._last_platform_offset = (0.0, 0.0)
            return (0.0, 0.0)

        max_disp = self._platform_cfg.max_px_per_frame
        m_type = self._platform_cfg.motion_type.upper()

        if m_type == "LINEAR":
            # Sinusoidal oscillation along a line representing platform roll/pitch drift
            # Period ~2.0 seconds, velocity bounded by max_disp
            omega = 2.0 * math.pi / 2.0
            dx = max_disp * math.sin(omega * self._time)
            dy = max_disp * 0.5 * math.cos(omega * self._time)
        elif m_type == "CIRCULAR":
            omega = 2.0 * math.pi / 3.0
            dx = max_disp * math.cos(omega * self._time)
            dy = max_disp * math.sin(omega * self._time)
        elif m_type == "RANDOM":
            dx = float(self._rng_platform.uniform(-max_disp, max_disp))
            dy = float(self._rng_platform.uniform(-max_disp, max_disp))
        else:
            dx = 0.0
            dy = 0.0

        # Enforce PS hard limit of +/- 20 pixels/frame
        dx = float(np.clip(dx, -defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME, defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME))
        dy = float(np.clip(dy, -defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME, defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME))

        self._last_platform_offset = (dx, dy)
        return (dx, dy)

    def compute_camera_jitter(self) -> Tuple[float, float]:
        """
        Stage 2: Camera Jitter (Geometric).
        High-frequency frame-to-frame vibration.
        PS Row 23: max +/- 20 px/frame.
        """
        if not self._jitter_cfg.enabled:
            self._last_jitter_offset = (0.0, 0.0)
            return (0.0, 0.0)

        max_jitter = self._jitter_cfg.max_px_per_frame
        # Sample zero-mean normal jitter scaled so 3*sigma ~ max_jitter
        sigma = max_jitter / 3.0 if max_jitter > 0 else 0.0
        jx = float(self._rng_jitter.normal(0.0, sigma))
        jy = float(self._rng_jitter.normal(0.0, sigma))

        # Hard clip to +/- max_jitter and PS maximum of +/- 20 px/frame
        limit = min(max_jitter, defaults.JITTER_MAX_PX_PER_FRAME)
        jx = float(np.clip(jx, -limit, limit))
        jy = float(np.clip(jy, -limit, limit))

        self._last_jitter_offset = (jx, jy)
        return (jx, jy)

    def apply_geometric_disturbances(
        self,
        cam_world_x: float,
        cam_world_y: float,
        dt: float,
    ) -> Tuple[float, float]:
        """
        Combined Stages 1 & 2: Platform Motion + Jitter.
        Shifts camera world position prior to viewport extraction.
        """
        self._time += dt
        plat_dx, plat_dy = self.compute_platform_motion(dt)
        jit_dx, jit_dy = self.compute_camera_jitter()

        eff_x = cam_world_x + plat_dx + jit_dx
        eff_y = cam_world_y + plat_dy + jit_dy
        return (eff_x, eff_y)

    # -----------------------------------------------------------------------
    # 4. Atmospheric Degradation (IPC)
    # -----------------------------------------------------------------------

    def apply_atmospheric_degradation(self, frame: np.ndarray) -> np.ndarray:
        """
        Stage 4: Atmospheric Degradation (Pixel).
        Applies contrast reduction and brightness shift.
        PS Row 24: Clear, Haze, Fog, Rain, Low light.
        """
        cond = self._atmos_cfg.condition.upper()

        if cond == AtmosphericCondition.CLEAR.value or cond == "CLEAR":
            contrast = 1.0
            offset = 0
        elif cond == AtmosphericCondition.HAZE.value or cond == "HAZE":
            contrast = (
                self._atmos_cfg.contrast_factor
                if self._atmos_cfg.contrast_factor is not None
                else defaults.ATMOS_HAZE_CONTRAST_FACTOR
            )
            offset = (
                self._atmos_cfg.brightness_offset
                if self._atmos_cfg.brightness_offset is not None
                else defaults.ATMOS_HAZE_BRIGHTNESS_OFFSET
            )
        elif cond == AtmosphericCondition.FOG.value or cond == "FOG":
            contrast = (
                self._atmos_cfg.contrast_factor
                if self._atmos_cfg.contrast_factor is not None
                else defaults.ATMOS_FOG_CONTRAST_FACTOR
            )
            offset = (
                self._atmos_cfg.brightness_offset
                if self._atmos_cfg.brightness_offset is not None
                else defaults.ATMOS_FOG_BRIGHTNESS_OFFSET
            )
        elif cond == AtmosphericCondition.RAIN.value or cond == "RAIN":
            contrast = (
                self._atmos_cfg.contrast_factor
                if self._atmos_cfg.contrast_factor is not None
                else defaults.ATMOS_RAIN_CONTRAST_FACTOR
            )
            offset = (
                self._atmos_cfg.brightness_offset
                if self._atmos_cfg.brightness_offset is not None
                else defaults.ATMOS_RAIN_BRIGHTNESS_OFFSET
            )
        elif cond == AtmosphericCondition.LOW_LIGHT.value or cond == "LOW_LIGHT":
            contrast = (
                self._atmos_cfg.contrast_factor
                if self._atmos_cfg.contrast_factor is not None
                else defaults.ATMOS_LOW_LIGHT_CONTRAST_FACTOR
            )
            offset = (
                self._atmos_cfg.brightness_offset
                if self._atmos_cfg.brightness_offset is not None
                else defaults.ATMOS_LOW_LIGHT_BRIGHTNESS_OFFSET
            )
        else:
            contrast = 1.0
            offset = 0

        if contrast == 1.0 and offset == 0:
            return frame.copy()

        degraded = frame.astype(np.float32) * contrast + offset
        return np.clip(degraded, 0.0, 255.0).astype(np.uint8)

    # -----------------------------------------------------------------------
    # 5. Poisson Noise (IPC, Signal-Dependent Shot Noise)
    # -----------------------------------------------------------------------

    def apply_poisson_noise(self, frame: np.ndarray) -> np.ndarray:
        """
        Stage 5: Poisson Noise (Signal-Dependent).
        Applied first among noise models because shot noise is inherent to arriving photons.
        """
        if not self._noise_cfg.poisson_enabled:
            return frame

        # Poisson distribution where lambda = pixel intensity
        float_frame = frame.astype(np.float32)
        # Avoid zero or negative lambda
        lambda_val = np.maximum(float_frame, 0.0)
        noisy = self._rng_noise.poisson(lambda_val)
        return np.clip(noisy, 0, 255).astype(np.uint8)

    # -----------------------------------------------------------------------
    # 6. Gaussian Noise (IPC, Additive Sensor Read Noise)
    # -----------------------------------------------------------------------

    def apply_gaussian_noise(self, frame: np.ndarray) -> np.ndarray:
        """
        Stage 6: Gaussian Noise (Additive Sensor Noise).
        Applied after optical signal degradation and shot noise.
        PS Row 22: Max standard deviation 20.
        """
        if not self._noise_cfg.gaussian_enabled:
            return frame

        sigma = float(np.clip(self._noise_cfg.gaussian_sigma, 0.0, defaults.NOISE_GAUSSIAN_MAX_SIGMA))
        if sigma <= 0.0:
            return frame

        noise = self._rng_noise.normal(0.0, sigma, frame.shape)
        noisy = frame.astype(np.float32) + noise
        return np.clip(noisy, 0.0, 255.0).astype(np.uint8)

    # -----------------------------------------------------------------------
    # 7. Salt & Pepper Noise (IPC, Impulse Noise)
    # -----------------------------------------------------------------------

    def apply_salt_and_pepper_noise(self, frame: np.ndarray) -> np.ndarray:
        """
        Stage 7: Salt & Pepper Noise (Impulse Noise).
        Applied last as final detector pixel defect / corruption layer.
        PS Row 21: around 10% of image.
        """
        if not self._noise_cfg.sp_enabled:
            return frame

        density = float(np.clip(self._noise_cfg.sp_density, 0.0, 1.0))
        if density <= 0.0:
            return frame

        result = frame.copy()
        # Generate random probability map for impulse corruptions
        prob = self._rng_noise.uniform(0.0, 1.0, frame.shape)
        half_density = density / 2.0

        # Pepper (0) for pixels < density/2
        result[prob < half_density] = 0
        # Salt (255) for pixels between density/2 and density
        result[(prob >= half_density) & (prob < density)] = 255

        return result

    # -----------------------------------------------------------------------
    # Full Pixel Disturbance Pipeline (Stages 4 -> 5 -> 6 -> 7)
    # -----------------------------------------------------------------------

    def apply_pixel_pipeline(self, clean_viewport: np.ndarray) -> np.ndarray:
        """
        Execute pixel disturbances in verified physical sequence:
          Stage 4: Atmospheric degradation
          Stage 5: Poisson noise (signal-dependent)
          Stage 6: Gaussian noise (additive)
          Stage 7: Salt & pepper noise (impulse)
        """
        # 4. Atmospheric degradation
        frame = self.apply_atmospheric_degradation(clean_viewport)
        # 5. Poisson noise
        frame = self.apply_poisson_noise(frame)
        # 6. Gaussian noise
        frame = self.apply_gaussian_noise(frame)
        # 7. Salt & Pepper noise
        frame = self.apply_salt_and_pepper_noise(frame)

        return frame
