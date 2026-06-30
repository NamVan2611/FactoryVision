"""Vision inspection package.

Public façade for the OpenCV-based inspection pipeline. The rest of the
application should import from :mod:`app.inspection` rather than the individual
submodules, so the internal structure can evolve without breaking callers
(Interface Segregation / stable public API).

Example
-------
>>> from app.inspection import InspectionEngine, create_camera_source
>>> engine = InspectionEngine()
>>> with create_camera_source("synthetic") as cam:
...     result = engine.inspect(cam.read())
>>> result.result  # PASS or FAIL
"""

from __future__ import annotations

from app.inspection.camera import (
    CameraSource,
    FileCameraSource,
    SyntheticCameraSource,
    WebcamCameraSource,
    create_camera_source,
)
from app.inspection.config import (
    ColorSpec,
    DimensionSpec,
    InspectionConfig,
    MissingPartSpec,
    ScratchSpec,
)
from app.inspection.detectors import (
    Detector,
    DetectorContext,
    default_detectors,
)
from app.inspection.engine import InspectionEngine
from app.inspection.preprocessing import preprocess

__all__ = [
    # Engine
    "InspectionEngine",
    "preprocess",
    # Detectors
    "Detector",
    "DetectorContext",
    "default_detectors",
    # Config
    "InspectionConfig",
    "ColorSpec",
    "DimensionSpec",
    "MissingPartSpec",
    "ScratchSpec",
    # Camera
    "CameraSource",
    "FileCameraSource",
    "WebcamCameraSource",
    "SyntheticCameraSource",
    "create_camera_source",
]
