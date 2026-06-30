"""Tunable configuration for the vision-inspection pipeline.

Centralising thresholds here keeps the detectors free of magic numbers and
makes the whole pipeline easy to calibrate per product / line without touching
algorithm code (Open/Closed Principle).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class ColorSpec:
    """Reference color (BGR) and acceptable deviation for color inspection."""

    target_bgr: Tuple[int, int, int] = (60, 140, 200)
    # Max mean per-channel deviation (0-255) before flagging a color defect.
    max_mean_deviation: float = 45.0


@dataclass(frozen=True)
class DimensionSpec:
    """Expected size of the main part as a fraction of the frame area."""

    min_area_ratio: float = 0.10
    max_area_ratio: float = 0.85
    # Expected aspect ratio (w/h) and tolerance band.
    target_aspect: float = 1.0
    aspect_tolerance: float = 0.35


@dataclass(frozen=True)
class MissingPartSpec:
    """Minimum number of distinct components expected on the part."""

    min_components: int = 1
    # Components smaller than this fraction of frame area are ignored as noise.
    min_component_area_ratio: float = 0.005


@dataclass(frozen=True)
class ScratchSpec:
    """Edge-density limits used to detect surface scratches."""

    canny_low: int = 50
    canny_high: int = 150
    # Edge-pixel ratio above this is considered an excessive-scratch defect.
    max_edge_density: float = 0.085


@dataclass(frozen=True)
class InspectionConfig:
    """Aggregate configuration consumed by :class:`InspectionEngine`."""

    color: ColorSpec = field(default_factory=ColorSpec)
    dimension: DimensionSpec = field(default_factory=DimensionSpec)
    missing_part: MissingPartSpec = field(default_factory=MissingPartSpec)
    scratch: ScratchSpec = field(default_factory=ScratchSpec)

    # Pre-processing.
    blur_kernel: int = 5            # Gaussian kernel size (odd).
    resize_width: int = 640         # Normalise frame width; 0 disables resize.

    # Decision.
    # A defect must reach this confidence to fail the part.
    fail_confidence_threshold: float = 0.55

    # Persistence.
    save_annotated: bool = True     # Save the overlay image for FAIL results.
