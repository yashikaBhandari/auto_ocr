"""Text refinement module.

Detects speckle noise / tiny components after preliminary enhancement and performs
morphological cleanup + optional Sauvola thresholding to improve OCR readability.

Detection heuristic:
- Compute adaptive (Otsu) binary then connected components.
- Count small components (area < SPECKLE_COMPONENT_MAX_AREA).
- If small components ratio > SPECKLE_RATIO_THRESHOLD => apply cleanup.

Processing:
- Sauvola threshold (skimage) to robustly binarize.
- Remove tiny components by area filtering.
- Morphological closing then opening to unify character strokes.
- Return cleaned 3-channel BGR image.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any

import cv2
import numpy as np

from .base_module import BaseModule
from ..utils import config

class TextRefineModule(BaseModule):
    name = "text_refine"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contrast = float(np.std(gray))
        # If already reasonably high contrast, skip refine to avoid over-processing
        if contrast > 65:
            return False, {"reason": "sufficient_contrast", "contrast_std": contrast}
        # Otsu segmentation
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Ensure text is dark (invert if majority dark)
        if np.mean(otsu) < 127:
            otsu = 255 - otsu
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(otsu, connectivity=8)
        if num_labels <= 1:
            return False, {"num_labels": num_labels, "contrast_std": contrast}
        areas = stats[1:, cv2.CC_STAT_AREA]
        small_mask = areas < config.SPECKLE_COMPONENT_MAX_AREA
        small_count = int(np.sum(small_mask))
        total = int(len(areas))
        ratio = float(small_count / total) if total else 0.0
        needs = ratio > config.SPECKLE_RATIO_THRESHOLD and small_count > 5
        return needs, {
            "num_components": total,
            "small_components": small_count,
            "speckle_ratio": ratio,
            "contrast_std": contrast,
            "threshold_used": "otsu",
        }

    def process(self, image, detect_meta: Dict[str, Any]):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Sauvola adaptive threshold
        try:
            from skimage.filters import threshold_sauvola  # local import
            thresh = threshold_sauvola(gray, window_size=config.SAUVOLA_WINDOW_SIZE, k=config.SAUVOLA_K)
            bin_img = (gray > thresh).astype('uint8') * 255
        except Exception:
            bin_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10)
        # Remove tiny components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_img, connectivity=8)
        cleaned = np.zeros_like(bin_img)
        removed = 0
        kept = 0
        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area >= config.SPECKLE_COMPONENT_MAX_AREA:
                cleaned[labels == label] = 255
                kept += 1
            else:
                removed += 1
        # Safety: if we removed too much (e.g., >70% of components) revert to original bin_img
        if (removed + kept) > 0 and removed / (removed + kept) > 0.7:
            cleaned = bin_img  # revert
            reverted = True
        else:
            reverted = False
        # Morphological smoothing only if not reverted
        if not reverted:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
        colored = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
        white_ratio = float(np.mean(cleaned > 0))
        return colored, {
            "applied": True,
            "components_removed": removed,
            "components_kept": kept,
            "pre_small_ratio": detect_meta.get("speckle_ratio"),
            "white_pixel_ratio": white_ratio,
            "reverted_cleanup": reverted,
            "method": "sauvola_cleanup" if 'thresh' in locals() else "adaptive_cleanup",
        }

__all__ = ["TextRefineModule"]
