"""Schemas describing the *output* of the vision-inspection pipeline.

These are framework-agnostic data containers shared by the inspection engine,
the service layer and the REST/WebSocket APIs. They intentionally do not depend
on OpenCV so they can be imported anywhere cheaply.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import DefectType, InspectionResult


class BoundingBox(BaseModel):
    """Axis-aligned rectangle in pixel coordinates (top-left origin)."""

    x: int = Field(..., ge=0, description="Left edge in pixels.")
    y: int = Field(..., ge=0, description="Top edge in pixels.")
    width: int = Field(..., gt=0, description="Box width in pixels.")
    height: int = Field(..., gt=0, description="Box height in pixels.")

    def as_xyxy(self) -> tuple[int, int, int, int]:
        """Return ``(x1, y1, x2, y2)`` corner representation."""
        return self.x, self.y, self.x + self.width, self.y + self.height


class Defect(BaseModel):
    """A single detected defect with its type, confidence and location."""

    type: DefectType
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None
    detail: Optional[str] = Field(None, description="Human-readable explanation.")


class InspectionResultDTO(BaseModel):
    """Complete result of inspecting one frame.

    Returned by :class:`~app.inspection.engine.InspectionEngine.inspect`.
    """

    result: InspectionResult
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Overall PASS/FAIL confidence.")
    defects: List[Defect] = Field(default_factory=list)
    processing_ms: float = Field(..., ge=0.0,
                                 description="Wall-clock processing time.")
    image_width: int = Field(..., gt=0)
    image_height: int = Field(..., gt=0)
    annotated_image_path: Optional[str] = Field(
        None, description="Path to the saved image with overlays, if persisted."
    )

    @property
    def is_pass(self) -> bool:
        """Convenience flag: ``True`` when the part passed inspection."""
        return self.result is InspectionResult.PASS

    @property
    def primary_defect(self) -> DefectType:
        """The highest-confidence defect type, or ``NONE`` when passing."""
        if not self.defects:
            return DefectType.NONE
        return max(self.defects, key=lambda d: d.confidence).type
