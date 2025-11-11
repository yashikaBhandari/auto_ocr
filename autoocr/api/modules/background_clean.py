"""Background Clean Module: Shadow, Lighting, and Bleed-Through Removal.

Handles:
- Shadow removal (dark shadows and folds)
- Uneven lighting correction
- Bleed-through text removal (text from backside)
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np
from .base_module import BaseModule


class BackgroundCleanModule(BaseModule):
    """Cleans backgrounds: shadows, uneven lighting, bleed-through."""

    name = "background_clean"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect shadows, uneven lighting, and bleed-through."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Detect shadows using low brightness regions
        shadow_mask = gray < 50
        shadow_ratio = np.sum(shadow_mask) / (gray.shape[0] * gray.shape[1])

        # Detect uneven lighting (high variance in brightness)
        # Compare corners to center
        h, w = gray.shape
        corner_brightness = np.mean([
            np.mean(gray[:h//4, :w//4]),
            np.mean(gray[:h//4, -w//4:]),
            np.mean(gray[-h//4:, :w//4]),
            np.mean(gray[-h//4:, -w//4:])
        ])
        center_brightness = np.mean(gray[h//4:-h//4, w//4:-w//4])
        lighting_diff = abs(corner_brightness - center_brightness) / (center_brightness + 1e-6)

        # Detect bleed-through (repeated patterns visible)
        # Look for faint text-like patterns
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        diff = cv2.absdiff(gray, blurred)
        bleed_ratio = np.sum(diff > 10) / (gray.shape[0] * gray.shape[1])

        should_process = bool(shadow_ratio > 0.1 or lighting_diff > 0.2 or bleed_ratio > 0.15)

        return should_process, {
            "shadow_ratio": float(round(shadow_ratio, 3)),
            "lighting_diff": float(round(lighting_diff, 3)),
            "bleed_ratio": float(round(bleed_ratio, 3)),
            "has_shadows": bool(shadow_ratio > 0.1),
            "has_uneven_lighting": bool(lighting_diff > 0.2),
            "has_bleed_through": bool(bleed_ratio > 0.15),
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Remove shadows, fix lighting, and remove bleed-through."""
        result = image.copy()
        gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY) if len(result.shape) == 3 else result

        # Step 1: Uneven Lighting Correction (do first)
        if detect_meta.get("has_uneven_lighting"):
            result = self._correct_uneven_lighting(result, gray)

        # Step 2: Shadow Removal
        if detect_meta.get("has_shadows"):
            result = self._remove_shadows(result)

        # Step 3: Bleed-Through Removal
        if detect_meta.get("has_bleed_through"):
            result = self._remove_bleed_through(result)

        return result, {
            "shadows_removed": bool(detect_meta.get("has_shadows", False)),
            "lighting_corrected": bool(detect_meta.get("has_uneven_lighting", False)),
            "bleed_through_removed": bool(detect_meta.get("has_bleed_through", False)),
            "method": "Morphology + Illumination + Thresholding"
        }

    def _correct_uneven_lighting(self, image, gray):
        """Correct uneven lighting across the page."""
        # Create illumination map
        # Large morphological opening gives background estimate
        kernel_size = max(51, min(gray.shape) // 10)
        if kernel_size % 2 == 0:
            kernel_size += 1

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

        # Normalize background
        background = cv2.normalize(background, None, 1, 255, cv2.NORM_MINMAX)

        # Divide original by background (illumination correction)
        corrected_gray = cv2.divide(gray, background)
        corrected_gray = cv2.normalize(corrected_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # Apply slight CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        corrected_gray = clahe.apply(corrected_gray)

        # Convert back to BGR if needed
        if len(image.shape) == 3:
            result = cv2.cvtColor(corrected_gray, cv2.COLOR_GRAY2BGR)
        else:
            result = corrected_gray

        return result

    def _remove_shadows(self, image):
        """Remove dark shadows and folds."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Morphological opening to remove dark spots
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel, iterations=2)

        # Compare and enhance areas affected by shadows
        shadow_mask = cv2.absdiff(gray, opened)
        shadow_mask = cv2.threshold(shadow_mask, 30, 255, cv2.THRESH_BINARY)[1]

        # Dilate shadow mask
        shadow_mask = cv2.dilate(shadow_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)), iterations=1)

        # Inpaint
        if len(image.shape) == 3:
            result = cv2.inpaint(image, shadow_mask, 3, cv2.INPAINT_TELEA)
        else:
            result = cv2.inpaint(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), shadow_mask, 3, cv2.INPAINT_TELEA)

        return result

    def _remove_bleed_through(self, image):
        """Remove bleed-through text from backside."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply Sauvola binarization to separate foreground text
        from .binarize import BinarizeModule
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )

        # Morphological closing to connect text
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Find connected components (foreground text)
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(255 - closed, connectivity=8)

        # Create bleed-through mask (very faint text)
        bleed_mask = np.zeros_like(gray)
        min_area = 10
        for i in range(1, n_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_area:  # Very small = likely bleed-through
                bleed_mask[labels == i] = 255

        # Inpaint bleed-through
        if len(image.shape) == 3:
            result = cv2.inpaint(image, bleed_mask, 2, cv2.INPAINT_TELEA)
        else:
            result = cv2.inpaint(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), bleed_mask, 2, cv2.INPAINT_TELEA)

        return result


__all__ = ["BackgroundCleanModule"]
