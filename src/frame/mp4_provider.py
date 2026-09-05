"""
MP4 Frame Provider — Module 8 Video Adapter per Architecture v1.2 §4 and §6.

Decodes external MP4 video streams via OpenCV VideoCapture and adapts them to
the uniform IFrameProvider contract.

RESOLUTION & FPS AGNOSTIC:
Does NOT hard-code 640x480 or 30 FPS. Reads true video stream properties and
preserves arbitrary input dimensions (e.g. 320x240, 800x600, 1920x1080).
Converts multi-channel frames to monochrome uint8.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

import cv2
import numpy as np

from src.interfaces.strategy_interfaces import IFrameProvider
from src.frame.data_contracts import FramePacket, FrameSource


class MP4FrameProvider(IFrameProvider):
    """
    MP4FrameProvider (Module 8 - Video Adapter).

    Responsibilities:
      - Sequentially decode MP4 / video containers using OpenCV
      - Automatically convert RGB/BGR frames to monochrome uint8
      - Extract and expose true container resolution and framerate
      - Provide accurate timestamps (hardware container timestamp or fallback)
      - Enforce zero-copy frame immutability
      - Handle end-of-stream and corrupt/missing files cleanly
    """

    def __init__(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        self._file_path = file_path
        self._cap = cv2.VideoCapture(file_path)

        if not self._cap.isOpened():
            raise ValueError(f"Failed to open video file (unsupported codec or corrupt): {file_path}")

        # Extract container metadata
        raw_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        raw_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        raw_fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        raw_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self._width = raw_w if raw_w > 0 else 640
        self._height = raw_h if raw_h > 0 else 480
        # Sensible fallback if container does not provide valid FPS
        self._fps = raw_fps if raw_fps > 0.0 else 30.0
        self._total_frames = max(0, raw_count)

        self._frame_count = 0
        self._exhausted = False

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self._width, self._height)

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def file_path(self) -> str:
        return self._file_path

    def get_source_type(self) -> str:
        return FrameSource.MP4_FILE.value

    def is_exhausted(self) -> bool:
        return self._exhausted

    def reset(self) -> None:
        """Seek back to frame 0 and reset playback state."""
        if self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._frame_count = 0
        self._exhausted = False

    def close(self) -> None:
        """Release OpenCV video capture handle."""
        if hasattr(self, "_cap") and self._cap.isOpened():
            self._cap.release()

    def get_next_frame(self) -> Optional[FramePacket]:
        """
        Decode and return the next sequential video frame as an immutable FramePacket.
        Returns None on end-of-stream or decode failure.
        """
        if self._exhausted or not self._cap.isOpened():
            return None

        # Capture container timestamp before decoding
        pos_msec = self._cap.get(cv2.CAP_PROP_POS_MSEC)

        ret, frame = self._cap.read()
        if not ret or frame is None:
            self._exhausted = True
            return None

        # Convert to monochrome uint8 if 3-channel (BGR)
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif len(frame.shape) == 3 and frame.shape[2] == 1:
            gray = frame.squeeze(axis=2)
        elif len(frame.shape) == 2:
            gray = frame
        else:
            # Multi-channel edge case (e.g. RGBA)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

        actual_h, actual_w = gray.shape[:2]
        self._width = actual_w
        self._height = actual_h

        # Compute timestamp: prefer hardware timestamp; fallback to frame_index / fps
        if pos_msec is not None and pos_msec > 0.0:
            timestamp = pos_msec / 1000.0
        else:
            timestamp = self._frame_count / self._fps

        # Enforce zero-copy read-only view
        gray.flags.writeable = False

        packet = FramePacket(
            frame_number=self._frame_count,
            timestamp=timestamp,
            image=gray,
            width=actual_w,
            height=actual_h,
            source=FrameSource.MP4_FILE,
        )

        self._frame_count += 1
        return packet
