"""Color Correction Module: White Balance, Faded Ink, and Color Normalization.

Handles:
- White balance correction (yellow, blue, faded colors)
- Faded ink restoration
- Color normalization across pages
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np
from .base_module import BaseModule


class ColorCorrectionModule(BaseModule):
    """Corrects color issues: white balance, fading, and normalization."""

    name = "color_correction"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect color issues: white balance problems, fading, etc."""
        if len(image.shape) == 2:
            # Grayscale image - no color correction needed
            return False, {"is_grayscale": True}

        # Analyze color channels
        b_mean = np.mean(image[:, :, 0])
        g_mean = np.mean(image[:, :, 1])
        r_mean = np.mean(image[:, :, 2])

        # Check for color cast
        # Yellow cast: high R and G, low B
        # Blue cast: high B, low R and G
        b_g_diff = abs(b_mean - g_mean)
        b_r_diff = abs(b_mean - r_mean)
        g_r_diff = abs(g_mean - r_mean)

        has_color_cast = bool(max(b_g_diff, b_r_diff, g_r_diff) > 30)

        # Check for fading (low overall intensity)
        intensity = (b_mean + g_mean + r_mean) / 3
        is_faded = bool(intensity < 100)

        should_process = bool(has_color_cast or is_faded)

        return should_process, {
            "color_cast_detected": has_color_cast,
            "fading_detected": is_faded,
            "b_mean": float(round(b_mean, 2)),
            "g_mean": float(round(g_mean, 2)),
            "r_mean": float(round(r_mean, 2)),
            "intensity": float(round(intensity, 2)),
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Apply color corrections."""
        if detect_meta.get("is_grayscale"):
            return image, {
                "color_correction_applied": False,
                "reason": "Grayscale image"
            }

        result = image.copy()

        # Step 1: White Balance Fix
        if detect_meta.get("color_cast_detected"):
            result = self._fix_white_balance(result)

        # Step 2: Faded Ink Restoration
        if detect_meta.get("fading_detected"):
            result = self._restore_faded_ink(result)

        # Step 3: Color Normalization
        result = self._normalize_color(result)

        return result, {
            "white_balance_fixed": bool(detect_meta.get("color_cast_detected", False)),
            "faded_ink_restored": bool(detect_meta.get("fading_detected", False)),
            "color_normalized": True,
            "method": "Gray_World + Contrast_Stretching + Histogram_Match"
        }

    def _fix_white_balance(self, image):
        """Fix white balance using gray world assumption."""
        # Convert to float
        img_float = image.astype(np.float32) / 255.0

        # Calculate mean of each channel
        b_mean = np.mean(img_float[:, :, 0])
        g_mean = np.mean(img_float[:, :, 1])
        r_mean = np.mean(img_float[:, :, 2])

        # Calculate gray value
        gray_value = (b_mean + g_mean + r_mean) / 3

        # Normalize channels
        if b_mean > 0:
            img_float[:, :, 0] = img_float[:, :, 0] * (gray_value / b_mean)
        if g_mean > 0:
            img_float[:, :, 1] = img_float[:, :, 1] * (gray_value / g_mean)
        if r_mean > 0:
            img_float[:, :, 2] = img_float[:, :, 2] * (gray_value / r_mean)

        # Clip and convert back
        img_float = np.clip(img_float, 0, 1)
        result = (img_float * 255).astype(np.uint8)

        return result

    def _restore_faded_ink(self, image):
        """Restore faded ink by stretching contrast."""
        # Convert to LAB color space (L = lightness, A/B = color)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Separate channels
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel (brightness)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        # Optionally enhance a and b channels slightly
        a_enhanced = cv2.normalize(a, None, 0, 255, cv2.NORM_MINMAX)
        b_enhanced = cv2.normalize(b, None, 0, 255, cv2.NORM_MINMAX)

        # Merge channels
        lab_enhanced = cv2.merge([l_enhanced, a_enhanced, b_enhanced])

        # Convert back to BGR
        result = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        return result

    def _normalize_color(self, image):
        """Normalize color across the image."""
        # Convert to LAB for better color normalization
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Normalize each channel independently
        l, a, b = cv2.split(lab)

        # Normalize to range [0, 255]
        l = cv2.normalize(l, None, 0, 255, cv2.NORM_MINMAX)
        a = cv2.normalize(a, None, 0, 255, cv2.NORM_MINMAX)
        b = cv2.normalize(b, None, 0, 255, cv2.NORM_MINMAX)

        # Merge and convert back
        lab_normalized = cv2.merge([l, a, b])
        result = cv2.cvtColor(lab_normalized, cv2.COLOR_LAB2BGR)

        return result


__all__ = ["ColorCorrectionModule"]
