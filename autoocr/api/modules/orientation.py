"""Orientation detection & correction using Tesseract OSD.

Detection:
- Use pytesseract.image_to_osd output and parse 'Rotate: <deg>'.
- If angle in {90, 180, 270} -> needs rotation.
Processing:
- Rotate image to 0° upright via cv2.rotate or warpAffine.

Notes:
- Requires tesseract installed on system path.
- If OSD fails, gracefully skip.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import re

import cv2
import pytesseract

from .base_module import BaseModule

class OrientationModule(BaseModule):
    name = "orientation"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect if orientation correction is needed.

        Graceful fallback:
        - If tesseract isn't installed, return detected=False with reason.
        - If OSD parsing fails, return detected=False with embedded error.
        """
        # Check tesseract availability explicitly to avoid generic exception noise.
        try:
            _ = pytesseract.get_tesseract_version()
        except (pytesseract.pytesseract.TesseractNotFoundError, OSError):
            return False, {"reason": "tesseract_missing"}
        try:
            osd = pytesseract.image_to_osd(image)
            match = re.search(r"Rotate: (\d+)", osd)
            angle = int(match.group(1)) if match else 0
            needs = angle in (90, 180, 270)
            return needs, {"angle": angle, "osd": osd}
        except Exception as e:  # pylint: disable=broad-except
            return False, {"reason": "osd_failed", "error": str(e)}

    def process(self, image, detect_meta: Dict[str, Any]):
        angle = detect_meta.get("angle", 0)
        if angle == 0:
            return image, {"applied": False}
        # Map to cv2 rotations for multiples of 90
        if angle == 90:
            rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif angle == 180:
            rotated = cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        else:
            # Fallback: arbitrary angle (should not happen here)
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC)
        return rotated, {"applied": True, "original_angle": angle}

__all__ = ["OrientationModule"]
