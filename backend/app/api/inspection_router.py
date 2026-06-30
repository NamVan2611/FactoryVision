"""Inspection endpoints: run the vision pipeline and persist results.

``POST /api/inspection`` accepts a multipart image upload, runs it through the
:class:`~app.inspection.engine.InspectionEngine`, persists the outcome via
:class:`~app.services.InspectionService`, and returns the structured result.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.dependencies import InspectionServiceDep
from app.config import get_settings
from app.inspection.engine import InspectionEngine
from app.schemas.entities import InspectionRead
from app.schemas.vision import InspectionResultDTO
from app.utils import get_logger
from app.utils.exceptions import InspectionError

logger = get_logger(__name__)
router = APIRouter(prefix="/inspection", tags=["inspection"])

# A single shared engine instance is fine: it is stateless across calls and the
# detector pipeline is read-only after construction.
_settings = get_settings()
_engine = InspectionEngine(output_dir=_settings.defects_dir_path)


def _decode_image(raw: bytes) -> np.ndarray:
    """Decode raw bytes into a BGR image or raise :class:`InspectionError`."""
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise InspectionError("Uploaded file is not a decodable image.")
    return image


@router.post(
    "",
    response_model=InspectionResultDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Run vision inspection on an uploaded image",
)
async def run_inspection(
    service: InspectionServiceDep,
    machine_id: int = Form(..., description="Target machine id."),
    product_id: Optional[int] = Form(None),
    operator_id: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    image: UploadFile = File(..., description="Product image to inspect."),
) -> InspectionResultDTO:
    """Inspect ``image`` and persist the result for ``machine_id``."""
    raw = await image.read()
    if not raw:
        raise InspectionError("Empty image upload.")

    frame = _decode_image(raw)
    dto: InspectionResultDTO = _engine.inspect(frame)

    service.record(
        dto,
        machine_id=machine_id,
        product_id=product_id,
        operator_id=operator_id,
        notes=notes,
    )
    return dto


@router.get(
    "/{inspection_id}",
    response_model=InspectionRead,
    summary="Fetch a single inspection record",
)
async def get_inspection(
    inspection_id: int, service: InspectionServiceDep
) -> InspectionRead:
    """Return a stored inspection by id (404 if missing)."""
    record = service.get(inspection_id)
    return InspectionRead.model_validate(record)


__all__ = ["router"]
