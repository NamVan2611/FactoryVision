"""Image pre-processing helpers used by the inspection pipeline.

All functions are pure and operate on / return ``numpy.ndarray`` (BGR or
grayscale). Keeping them isolated makes them trivially unit-testable and
reusable by every detector.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.inspection.config import InspectionConfig


def decode_image(buffer: bytes) -> np.ndarray:
    """Decode raw image ``bytes`` (PNG/JPEG/...) into a BGR ndarray.

    Raises
    ------
    ValueError
        If the buffer cannot be decoded into an image.
    """
    array = np.frombuffer(buffer, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image buffer.")
    return image


def encode_image(image: np.ndarray, ext: str = ".jpg") -> bytes:
    """Encode a BGR ndarray back into compressed image ``bytes``."""
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        raise ValueError(f"Could not encode image to '{ext}'.")
    return encoded.tobytes()


def resize_to_width(image: np.ndarray, width: int) -> np.ndarray:
    """Resize keeping aspect ratio so the output width equals ``width``.

    A ``width`` of 0 (or one matching the input) returns the image unchanged.
    """
    if width <= 0:
        return image
    h, w = image.shape[:2]
    if w == width:
        return image
    scale = width / float(w)
    return cv2.resize(image, (width, int(round(h * scale))),
                      interpolation=cv2.INTER_AREA)


def to_gray(image: np.ndarray) -> np.ndarray:
    """Convert a BGR image to single-channel grayscale."""
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise(image: np.ndarray, kernel: int) -> np.ndarray:
    """Apply Gaussian blur with an odd ``kernel`` size (no-op if <= 1)."""
    if kernel <= 1:
        return image
    k = kernel if kernel % 2 == 1 else kernel + 1
    return cv2.GaussianBlur(image, (k, k), 0)


def foreground_mask(gray: np.ndarray) -> np.ndarray:
    """Return a binary mask isolating the part from the background.

    Uses Otsu thresholding followed by a morphological close to fill holes.
    """
    _, mask = cv2.threshold(gray, 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Heuristic: parts are usually darker than a bright background; if the
    # mask is mostly white, invert so the part becomes the foreground.
    if np.count_nonzero(mask) > mask.size * 0.5:
        mask = cv2.bitwise_not(mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)


def preprocess(image: np.ndarray, config: InspectionConfig) -> tuple[np.ndarray, np.ndarray]:
    """Normalise an input frame for inspection.

    Returns
    -------
    tuple
        ``(bgr_resized, gray_blurred)`` -- the resized color image (for
        annotation / color analysis) and a denoised grayscale copy used by the
        geometry / scratch detectors.
    """
    bgr = resize_to_width(image, config.resize_width)
    gray = denoise(to_gray(bgr), config.blur_kernel)
    return bgr, gray
