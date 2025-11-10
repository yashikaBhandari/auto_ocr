"""Noise detection & reduction.

Detection (simplistic):
- Variance of Laplacian measures local detail. Low variance often indicates blur, but
  for our heuristic we treat very low value as 'needs enhancement/denoise'.
- Could extend with entropy or FFT-based noise estimation later.

Processing:
- Apply fastNlMeansDenoisingColored (works reasonably on scanned docs) or fallback to median blur.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any

import cv2
import numpy as np

from .base_module import BaseModule
from ..utils import config

class DenoiseModule(BaseModule):
    name = "denoise"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Always return True but report metrics so processing can adapt its strength."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        noise_level = float(np.mean(np.abs(gray.astype(np.float32) - blurred.astype(np.float32))))
        return True, {
            "laplacian_variance": lap_var,
            "noise_level": noise_level,
            "high_noise": noise_level > config.NOISE_LEVEL_THRESHOLD,
            "blurry": lap_var < config.LAPLACIAN_VARIANCE_NOISE_THRESHOLD,
        }

    def process(self, image, detect_meta: Dict[str, Any]):
        strength = 10 if detect_meta.get("high_noise") else 5
        try:
            denoised = cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)
            return denoised, {"applied": True, "method": "fastNlMeans", "strength": strength}
        except Exception:  # pylint: disable=broad-except
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            k = 5 if detect_meta.get("high_noise") else 3
            median = cv2.medianBlur(gray, k)
            restored = cv2.cvtColor(median, cv2.COLOR_GRAY2BGR)
            return restored, {"applied": True, "method": "median_fallback", "kernel": k}

__all__ = ["DenoiseModule"]
