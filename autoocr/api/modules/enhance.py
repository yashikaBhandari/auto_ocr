"""Contrast enhancement & sharpening module.

Detection:
- Standard deviation of grayscale histogram. If below threshold -> low contrast.
Processing:
- CLAHE for localized contrast improvement.
- Unsharp masking for sharpening (amount, gaussian kernel from config).
"""
from __future__ import annotations
from typing import Tuple, Dict, Any

import cv2
import numpy as np

from .base_module import BaseModule
from ..utils import config

class EnhanceModule(BaseModule):
    name = "enhance"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Always return True with metrics; processing adapts intensity to avoid over-enhancing."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contrast = float(np.std(gray))
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))
        low_contrast = contrast < config.LOW_CONTRAST_STD_THRESHOLD
        blurry = lap_var < config.LAPLACIAN_VARIANCE_SHARPNESS_THRESHOLD
        bad_brightness = brightness < config.BRIGHTNESS_LOW_THRESHOLD or brightness > config.BRIGHTNESS_HIGH_THRESHOLD
        return True, {
            "contrast_std": contrast,
            "laplacian_variance": lap_var,
            "brightness_mean": brightness,
            "low_contrast": low_contrast,
            "blurry": blurry,
            "bad_brightness": bad_brightness,
        }

    def process(self, image, detect_meta: Dict[str, Any]):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Adaptive CLAHE clip limit: lower if already high contrast
        base_clip = config.CLAHE_CLIP_LIMIT
        clip_limit = base_clip * (0.6 if detect_meta.get("contrast_std", 0) > 70 else 1.0)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=config.CLAHE_TILE_GRID_SIZE)
        cl = clahe.apply(gray)
        if detect_meta.get("bad_brightness"):
            cl = cv2.normalize(cl, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        # Adaptive sharpening amount
        amount = config.UNSHARP_AMOUNT
        if detect_meta.get("contrast_std", 0) > 70 and not detect_meta.get("low_contrast"):
            amount = 1.1  # milder sharpening
        blurred = cv2.GaussianBlur(cl, config.UNSHARP_GAUSSIAN_KERNEL, config.UNSHARP_SIGMA)
        sharpened = cv2.addWeighted(cl, amount, blurred, - (amount - 1), 0)
        colored = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        post_contrast = float(np.std(sharpened))
        return colored, {
            "applied": True,
            "pre_contrast": detect_meta.get("contrast_std"),
            "post_contrast": post_contrast,
            "adaptive_clip_limit": clip_limit,
            "adaptive_unsharp_amount": amount,
        }

__all__ = ["EnhanceModule"]
