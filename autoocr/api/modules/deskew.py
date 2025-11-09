"""Deskew detection & correction.

Detection strategy:
1. Convert to grayscale -> binary (adaptive or Otsu) emphasizing text.
2. Use Canny edges + Hough transform OR compute minAreaRect on non-white pixels.
3. Aggregate angles; compute average deviation from horizontal.
4. If |angle| > threshold (config) -> apply deskew.

Processing:
- Rotate by negative detected angle using affine transform.

Limitations:
- For heavy perspective distortion, a perspective module would be needed (future extension).
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import math

import cv2
import numpy as np

from .base_module import BaseModule
from ..utils import config

class DeskewModule(BaseModule):
    name = "deskew"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Binary inversion to highlight text
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        # Invert so text ~1
        inverted = 255 - thresh
        coords = np.column_stack(np.where(inverted > 0))
        if coords.size == 0:
            return False, {"reason": "no_text_pixels"}
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        # minAreaRect angle peculiarity
        if angle < -45:
            angle = 90 + angle
        # We want small angle near 0
        needs = abs(angle) > config.SKEW_DEGREE_MIN
        return needs, {"angle": float(angle)}

    def process(self, image, detect_meta: Dict[str, Any]):
        angle = detect_meta.get("angle", 0.0)
        if abs(angle) <= config.SKEW_DEGREE_MIN:
            return image, {"applied": False}
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)  # rotate by angle returned (already sign adjusted)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated, {"applied": True, "deskew_angle": angle}

__all__ = ["DeskewModule"]
