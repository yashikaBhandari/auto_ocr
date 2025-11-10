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
        
        # Step 1: Remove background dots using morphological operations
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to separate text from background
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                      cv2.THRESH_BINARY, 25, 10)
        
        # Remove small dots using morphological opening (keeps text, removes small dots)
        kernel = np.ones((2, 2), np.uint8)
        dots_removed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Apply median blur to smooth remaining noise
        smoothed = cv2.medianBlur(dots_removed, 3)
        
        # Convert back to BGR for further processing
        dots_cleaned = cv2.cvtColor(smoothed, cv2.COLOR_GRAY2BGR)
        
        # Step 2: Apply regular denoising on the dots-removed image
        try:
            denoised = cv2.fastNlMeansDenoisingColored(dots_cleaned, None, strength, strength, 7, 21)
            return denoised, {
                "applied": True, 
                "method": "fastNlMeans + dots_removal", 
                "strength": strength,
                "dots_removed": True
            }
        except Exception:  # pylint: disable=broad-except
            k = 5 if detect_meta.get("high_noise") else 3
            median = cv2.medianBlur(smoothed, k)
            restored = cv2.cvtColor(median, cv2.COLOR_GRAY2BGR)
            return restored, {
                "applied": True, 
                "method": "median_fallback + dots_removal", 
                "kernel": k,
                "dots_removed": True
            }

__all__ = ["DenoiseModule"]
