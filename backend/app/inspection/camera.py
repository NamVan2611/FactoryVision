"""Camera sources for acquiring frames to inspect.

Defines a small abstraction (:class:`CameraSource`) with three concrete
implementations so the rest of the system never depends on a physical camera:

* :class:`FileCameraSource`   -- replays images from a directory.
* :class:`SyntheticCameraSource` -- generates parts on the fly (PASS + defects).
* :class:`WebcamCameraSource` -- reads from a real OpenCV-compatible device.

The Dependency Inversion Principle lets the service layer accept any
``CameraSource`` and remain testable without hardware.
"""

from __future__ import annotations

import abc
import itertools
import random
from pathlib import Path
from typing import Iterable, List, Optional

import cv2
import numpy as np

from app.utils.exceptions import CameraError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


class CameraSource(abc.ABC):
    """Abstract frame source yielding BGR ``numpy`` images."""

    @abc.abstractmethod
    def read(self) -> np.ndarray:
        """Return the next frame as a BGR ndarray.

        Raises
        ------
        CameraError
            If no frame can be produced.
        """
        raise NotImplementedError

    def release(self) -> None:
        """Release any underlying resources (no-op by default)."""

    def __enter__(self) -> "CameraSource":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()


class FileCameraSource(CameraSource):
    """Cycles through image files found in a directory."""

    def __init__(self, directory: Path, loop: bool = True) -> None:
        self._directory = Path(directory)
        if not self._directory.is_dir():
            raise CameraError(f"Image directory not found: {self._directory}")
        self._files: List[Path] = sorted(
            p for p in self._directory.iterdir()
            if p.suffix.lower() in _IMAGE_EXTENSIONS
        )
        if not self._files:
            raise CameraError(f"No images in directory: {self._directory}")
        self._iter: Iterable[Path] = (
            itertools.cycle(self._files) if loop else iter(self._files)
        )

    def read(self) -> np.ndarray:
        try:
            path = next(iter(self._iter))  # type: ignore[arg-type]
        except StopIteration as exc:
            raise CameraError("No more images to read.") from exc
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise CameraError(f"Failed to read image: {path}")
        return image


class WebcamCameraSource(CameraSource):
    """Reads frames from a physical / virtual OpenCV capture device."""

    def __init__(self, device_index: int = 0) -> None:
        self._capture = cv2.VideoCapture(device_index)
        if not self._capture.isOpened():
            raise CameraError(f"Cannot open camera device {device_index}.")

    def read(self) -> np.ndarray:
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraError("Failed to grab frame from webcam.")
        return frame

    def release(self) -> None:
        self._capture.release()


class SyntheticCameraSource(CameraSource):
    """Generates synthetic parts, randomly injecting defects.

    Useful for demos, tests and CI where no camera or dataset exists. Roughly
    ``defect_rate`` of frames will contain an injected defect.
    """

    def __init__(
        self,
        size: int = 480,
        defect_rate: float = 0.3,
        seed: Optional[int] = None,
    ) -> None:
        self._size = size
        self._defect_rate = max(0.0, min(1.0, defect_rate))
        self._rng = random.Random(seed)

    def read(self) -> np.ndarray:
        canvas = np.full((self._size, self._size, 3), 240, dtype=np.uint8)
        margin = self._size // 6
        top_left = (margin, margin)
        bottom_right = (self._size - margin, self._size - margin)
        # Reference part color (BGR) matching the default ColorSpec target.
        color = (60, 140, 200)

        inject = self._rng.random() < self._defect_rate
        defect = self._rng.choice(
            ["color", "size", "missing", "scratch"]
        ) if inject else None

        if defect == "color":
            color = (200, 60, 60)  # Strong blue shift.
        if defect == "size":
            # Shrink the part well below the min area ratio.
            shrink = self._size // 4
            top_left = (top_left[0] + shrink, top_left[1] + shrink)
            bottom_right = (bottom_right[0] - shrink, bottom_right[1] - shrink)

        if defect != "missing":
            cv2.rectangle(canvas, top_left, bottom_right, color, cv2.FILLED)

        if defect == "scratch":
            for _ in range(60):
                p1 = (self._rng.randint(margin, self._size - margin),
                      self._rng.randint(margin, self._size - margin))
                p2 = (p1[0] + self._rng.randint(-40, 40),
                      p1[1] + self._rng.randint(-40, 40))
                cv2.line(canvas, p1, p2, (30, 30, 30), 1)

        logger.debug("Synthetic frame generated (defect=%s)", defect)
        return canvas


def create_camera_source(
    kind: str,
    *,
    directory: Optional[Path] = None,
    device_index: int = 0,
    defect_rate: float = 0.3,
) -> CameraSource:
    """Factory returning a configured :class:`CameraSource`.

    Parameters
    ----------
    kind:
        One of ``"file"``, ``"webcam"`` or ``"synthetic"``.
    """
    normalized = kind.strip().lower()
    if normalized == "file":
        if directory is None:
            raise CameraError("'file' camera requires a directory.")
        return FileCameraSource(directory)
    if normalized == "webcam":
        return WebcamCameraSource(device_index)
    if normalized == "synthetic":
        return SyntheticCameraSource(defect_rate=defect_rate)
    raise CameraError(f"Unknown camera kind: {kind!r}")
