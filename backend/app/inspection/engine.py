"""The inspection engine: orchestrates pre-processing, detectors and decision.

This is the single entry point the service / API layer uses. It is fully
decoupled from FastAPI, the database and the camera, which keeps it unit
testable and reusable.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import List, Optional, Sequence

import cv2
import numpy as np

from app.inspection.config import InspectionConfig
from app.inspection.detectors import Detector, DetectorContext, default_detectors
from app.inspection.preprocessing import preprocess
from app.models.enums import InspectionResult
from app.schemas.vision import Defect, InspectionResultDTO
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Overlay colors (BGR).
_COLOR_FAIL = (0, 0, 255)
_COLOR_TEXT_BG = (0, 0, 0)


class InspectionEngine:
    """Run a configurable pipeline of detectors over a single frame."""

    def __init__(
        self,
        config: Optional[InspectionConfig] = None,
        detectors: Optional[Sequence[Detector]] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Create an engine.

        Parameters
        ----------
        config:
            Threshold configuration. Defaults to :class:`InspectionConfig`.
        detectors:
            Detector pipeline. Defaults to :func:`default_detectors`.
        output_dir:
            Directory where annotated FAIL images are written.
        """
        self._config = config or InspectionConfig()
        self._detectors: List[Detector] = list(detectors or default_detectors())
        self._output_dir = output_dir
        if self._output_dir is not None:
            self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config(self) -> InspectionConfig:
        """The active threshold configuration."""
        return self._config

    def inspect(self, image: np.ndarray) -> InspectionResultDTO:
        """Inspect a BGR ``image`` and return a structured result.

        The wall-clock processing time is measured and reported. Annotated
        images are persisted for FAIL results when ``config.save_annotated`` is
        set and an ``output_dir`` was provided.
        """
        start = time.perf_counter()

        bgr, gray = preprocess(image, self._config)
        ctx = DetectorContext(bgr=bgr, gray=gray, config=self._config)

        defects: List[Defect] = []
        for detector in self._detectors:
            try:
                defects.extend(detector.detect(ctx))
            except Exception:  # pragma: no cover - defensive isolation
                logger.exception(
                    "Detector %s failed; skipping.",
                    type(detector).__name__,
                )

        result, confidence = self._decide(defects)
        annotated_path = self._maybe_save(bgr, defects, result)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        h, w = bgr.shape[:2]
        dto = InspectionResultDTO(
            result=result,
            confidence=round(confidence, 4),
            defects=defects,
            processing_ms=round(elapsed_ms, 2),
            image_width=int(w),
            image_height=int(h),
            annotated_image_path=annotated_path,
        )
        logger.info(
            "Inspection %s | defects=%d | confidence=%.2f | %.1f ms",
            result.value, len(defects), dto.confidence, dto.processing_ms,
        )
        return dto

    def _decide(self, defects: List[Defect]) -> tuple[InspectionResult, float]:
        """Derive overall PASS/FAIL and a confidence score from defects."""
        failing = [d for d in defects
                   if d.confidence >= self._config.fail_confidence_threshold]
        if failing:
            confidence = max(d.confidence for d in failing)
            return InspectionResult.FAIL, confidence
        # PASS confidence = how far we are from the worst sub-threshold defect.
        worst = max((d.confidence for d in defects), default=0.0)
        return InspectionResult.PASS, 1.0 - worst

    def _maybe_save(
        self,
        bgr: np.ndarray,
        defects: List[Defect],
        result: InspectionResult,
    ) -> Optional[str]:
        """Persist an annotated image for FAIL results; return its path."""
        if (
            result is not InspectionResult.FAIL
            or not self._config.save_annotated
            or self._output_dir is None
        ):
            return None
        annotated = self.annotate(bgr, defects)
        filename = f"fail_{uuid.uuid4().hex[:12]}.jpg"
        path = self._output_dir / filename
        if not cv2.imwrite(str(path), annotated):
            logger.warning("Failed to write annotated image to %s", path)
            return None
        return str(path)

    @staticmethod
    def annotate(image: np.ndarray, defects: List[Defect]) -> np.ndarray:
        """Return a copy of ``image`` with bounding boxes and labels drawn."""
        canvas = image.copy()
        for defect in defects:
            label = f"{defect.type.value} {defect.confidence:.0%}"
            if defect.bounding_box is not None:
                x1, y1, x2, y2 = defect.bounding_box.as_xyxy()
                cv2.rectangle(canvas, (x1, y1), (x2, y2), _COLOR_FAIL, 2)
                _put_label(canvas, label, (x1, max(0, y1 - 6)))
            else:
                _put_label(canvas, label, (8, 22))
        return canvas


def _put_label(image: np.ndarray, text: str, origin: tuple[int, int]) -> None:
    """Draw ``text`` with a filled background for readability."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.5, 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = origin
    cv2.rectangle(image, (x, y - th - baseline), (x + tw, y + baseline),
                  _COLOR_TEXT_BG, cv2.FILLED)
    cv2.putText(image, text, (x, y), font, scale, _COLOR_FAIL,
                thickness, cv2.LINE_AA)
