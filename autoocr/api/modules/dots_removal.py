"""Background dots removal module.

Removes small background dots/speckles that interfere with OCR while preserving:
- Text characters
- Legitimate punctuation (periods, commas)
- Important document elements

Uses multiple techniques:
1. Morphological operations (opening) to remove small isolated dots
2. Connected components analysis to filter by area
3. Adaptive thresholding for better text/background separation
"""
from __future__ import annotations
from typing import Tuple, Dict, Any

import cv2
import numpy as np

from .base_module import BaseModule


class DotsRemovalModule(BaseModule):
    name = "dots_removal"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect presence of background dots/speckles."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply threshold to find potential dots
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Find connected components
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

        # Count very small components (likely dots)
        small_dots = 0
        min_area = 5  # pixels
        max_dot_area = 20  # max area for a "dot"

        for i in range(1, n_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if min_area < area < max_dot_area:
                small_dots += 1

        # Calculate density of dots
        total_pixels = gray.shape[0] * gray.shape[1]
        dots_density = small_dots / (total_pixels / 10000)  # per 100x100 px area

        has_dots = small_dots > 50 or dots_density > 2.0

        return has_dots, {
            "small_components": small_dots,
            "dots_density": round(dots_density, 2),
            "threshold_detection": "background_dots" if has_dots else "clean"
        }

    def process(self, image, detect_meta: Dict[str, Any]):
        """Remove background dots using multi-stage approach."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Stage 1: Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY, 25, 10
        )

        # Stage 2: Morphological opening to remove small dots
        kernel_small = np.ones((2, 2), np.uint8)
        opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_small, iterations=2)

        # Stage 3: Connected components filtering
        # Invert for labeling (text should be foreground)
        inverted = cv2.bitwise_not(opened)
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            inverted, connectivity=8
        )

        # Create output image
        cleaned = np.ones_like(gray) * 255

        # Filter components by area
        min_area = 15  # Keep components larger than this
        components_removed = 0

        for i in range(1, n_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_area:
                # Keep this component (it's text or legitimate punctuation)
                cleaned[labels == i] = 0
            else:
                components_removed += 1

        # Stage 4: Median blur for final smoothing
        final = cv2.medianBlur(cleaned, 3)

        # Convert back to BGR
        result = cv2.cvtColor(final, cv2.COLOR_GRAY2BGR)

        return result, {
            "method": "morphology + connected_components",
            "components_removed": components_removed,
            "min_area_kept": min_area,
            "stages_applied": ["adaptive_threshold", "morphological_opening", "component_filtering", "median_blur"]
        }


__all__ = ["DotsRemovalModule"]
