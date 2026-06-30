"""Defect detectors implemented as interchangeable strategies.

Each detector receives a :class:`DetectorContext` (the pre-processed frame plus
shared artefacts such as the foreground mask) and returns a list of
:class:`~app.schemas.vision.Defect`. The :class:`InspectionEngine` simply runs
all registered detectors, satisfying the Open/Closed Principle: adding a new
inspection only means adding a new ``Detector`` subclass.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import List

import cv2
import numpy as np

from app.inspection.config import InspectionConfig
from app.inspection.preprocessing import foreground_mask
from app.models.enums import DefectType
from app.schemas.vision import BoundingBox, Defect


@dataclass
class DetectorContext:
    """Shared, lazily-built artefacts passed to every detector."""

    bgr: np.ndarray
    gray: np.ndarray
    config: InspectionConfig

    _mask: np.ndarray | None = None

    @property
    def mask(self) -> np.ndarray:
        """Cached foreground mask of the part."""
        if self._mask is None:
            self._mask = foreground_mask(self.gray)
        return self._mask

    @property
    def area(self) -> int:
        """Total frame area in pixels."""
        h, w = self.gray.shape[:2]
        return h * w


def _largest_contour(mask: np.ndarray):
    """Return the largest external contour in ``mask`` or ``None``."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


class Detector(abc.ABC):
    """Abstract base class for all defect detectors."""

    #: Defect type this detector is responsible for.
    defect_type: DefectType

    @abc.abstractmethod
    def detect(self, ctx: DetectorContext) -> List[Defect]:
        """Analyse ``ctx`` and return zero or more defects."""
        raise NotImplementedError


class ColorDetector(Detector):
    """Flags parts whose mean color deviates from the reference spec."""

    defect_type = DefectType.COLOR

    def detect(self, ctx: DetectorContext) -> List[Defect]:
        spec = ctx.config.color
        # Sample only the foreground so the background does not skew the mean.
        mean_bgr = cv2.mean(ctx.bgr, mask=ctx.mask)[:3]
        deviation = float(np.mean(np.abs(
            np.array(mean_bgr) - np.array(spec.target_bgr, dtype=float)
        )))
        if deviation <= spec.max_mean_deviation:
            return []
        # Map deviation onto a 0-1 confidence (saturating at 2x the threshold).
        confidence = min(1.0, deviation / (spec.max_mean_deviation * 2.0))
        return [Defect(
            type=self.defect_type,
            confidence=round(confidence, 4),
            detail=f"Mean color deviation {deviation:.1f} > "
                   f"{spec.max_mean_deviation:.1f}",
        )]


class DimensionDetector(Detector):
    """Flags parts whose size or aspect ratio is out of tolerance."""

    defect_type = DefectType.DIMENSION

    def detect(self, ctx: DetectorContext) -> List[Defect]:
        spec = ctx.config.dimension
        contour = _largest_contour(ctx.mask)
        if contour is None:
            return [Defect(type=self.defect_type, confidence=0.9,
                           detail="No part detected in frame.")]
        x, y, w, h = cv2.boundingRect(contour)
        area_ratio = cv2.contourArea(contour) / float(ctx.area)
        aspect = w / float(h) if h else 0.0
        box = BoundingBox(x=int(x), y=int(y), width=int(w), height=int(h))

        if area_ratio < spec.min_area_ratio:
            conf = min(1.0, (spec.min_area_ratio - area_ratio) /
                       spec.min_area_ratio + 0.5)
            return [Defect(type=self.defect_type, confidence=round(conf, 4),
                           bounding_box=box,
                           detail=f"Part too small (area ratio {area_ratio:.2f}).")]
        if area_ratio > spec.max_area_ratio:
            return [Defect(type=self.defect_type, confidence=0.7,
                           bounding_box=box,
                           detail=f"Part too large (area ratio {area_ratio:.2f}).")]

        aspect_err = abs(aspect - spec.target_aspect)
        if aspect_err > spec.aspect_tolerance:
            conf = min(1.0, aspect_err / (spec.aspect_tolerance * 2.0))
            return [Defect(type=self.defect_type, confidence=round(conf, 4),
                           bounding_box=box,
                           detail=f"Aspect ratio {aspect:.2f} out of tolerance.")]
        return []


class MissingPartDetector(Detector):
    """Flags parts that contain fewer components than expected."""

    defect_type = DefectType.MISSING_PART

    def detect(self, ctx: DetectorContext) -> List[Defect]:
        spec = ctx.config.missing_part
        min_area = spec.min_component_area_ratio * ctx.area
        contours, _ = cv2.findContours(ctx.mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        components = [c for c in contours if cv2.contourArea(c) >= min_area]
        if len(components) >= spec.min_components:
            return []
        missing = spec.min_components - len(components)
        confidence = min(1.0, 0.6 + 0.2 * missing)
        return [Defect(
            type=self.defect_type,
            confidence=round(confidence, 4),
            detail=f"Found {len(components)} component(s); "
                   f"expected >= {spec.min_components}.",
        )]


class ScratchDetector(Detector):
    """Flags excessive surface edges indicative of scratches."""

    defect_type = DefectType.SCRATCH

    def detect(self, ctx: DetectorContext) -> List[Defect]:
        spec = ctx.config.scratch
        edges = cv2.Canny(ctx.gray, spec.canny_low, spec.canny_high)
        # Restrict to the part surface so frame borders are not counted.
        edges = cv2.bitwise_and(edges, edges, mask=ctx.mask)
        part_pixels = int(np.count_nonzero(ctx.mask)) or 1
        density = float(np.count_nonzero(edges)) / part_pixels
        if density <= spec.max_edge_density:
            return []
        confidence = min(1.0, density / (spec.max_edge_density * 2.0))
        # Localise the densest scratch region for a bounding box.
        box = self._scratch_box(edges)
        return [Defect(
            type=self.defect_type,
            confidence=round(confidence, 4),
            bounding_box=box,
            detail=f"Edge density {density:.3f} > {spec.max_edge_density:.3f}",
        )]

    @staticmethod
    def _scratch_box(edges: np.ndarray) -> BoundingBox | None:
        """Bounding box around the largest cluster of edge pixels."""
        dilated = cv2.dilate(edges, np.ones((5, 5), np.uint8))
        contour = _largest_contour(dilated)
        if contour is None:
            return None
        x, y, w, h = cv2.boundingRect(contour)
        if w <= 0 or h <= 0:
            return None
        return BoundingBox(x=int(x), y=int(y), width=int(w), height=int(h))


def default_detectors() -> List[Detector]:
    """Return the standard detector pipeline in execution order."""
    return [
        DimensionDetector(),
        MissingPartDetector(),
        ColorDetector(),
        ScratchDetector(),
    ]
