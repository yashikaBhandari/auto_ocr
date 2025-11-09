"""Final adaptive binarization module.

Detection:
- Always returns True (can be made conditional if needed by analyzing background variance).
Processing:
- Adaptive Gaussian threshold -> binary image (returned still in 3-channel BGR for consistency).
"""
from __future__ import annotations
from typing import Tuple, Dict, Any

import cv2
import numpy as np
from ..utils import config

from .base_module import BaseModule

class BinarizeModule(BaseModule):
    name = "binarize"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contrast = float(np.std(gray))
        # Always apply but record contrast for downstream analysis
        return True, {"pre_binarize_contrast": contrast}

    def process(self, image, detect_meta: Dict[str, Any]):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Try Sauvola (Skimage) fallback to OpenCV adaptive if unavailable
        try:
            from skimage.filters import threshold_sauvola  # local import to keep startup light
            window_size = getattr(config, 'SAUVOLA_WINDOW_SIZE', 25)
            k = getattr(config, 'SAUVOLA_K', 0.2)
            thresh = threshold_sauvola(gray, window_size=window_size, k=k)
            bin_img = (gray > thresh).astype('uint8') * 255
        except Exception:  # pragma: no cover
            bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY, 15, 10)
        colored = cv2.cvtColor(bin_img, cv2.COLOR_GRAY2BGR)
        return colored, {"applied": True, "method": "sauvola" if 'thresh' in locals() else "adaptive_gaussian"}

__all__ = ["BinarizeModule"]
