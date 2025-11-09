"""Black edge detection & masking module.

Approach (detection):
1. Convert to grayscale.
2. Apply light threshold to separate dark pixels.
3. Find external contours.
4. Choose largest contour as candidate document region.
5. Compute contour area ratio vs full image.
   - If ratio < AREA_THRESHOLD -> black border likely present (extra dark outside region).
   - Else skip.

Approach (processing via masking, NOT cropping):
- Create a mask of the largest contour (document interior).
- Invert mask -> border mask.
- Paint border region white in the original image (preserves dimensions & alignment).

Advantages:
- Safe for downstream deskew/perspective since geometry unchanged.
- Avoid accidental text trimming.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np

from .base_module import BaseModule

class EdgeMaskModule(BaseModule):
    name = "edge_mask"

    def __init__(self, area_threshold: float = 0.90):
        self.area_threshold = area_threshold

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Threshold: keep bright -> 255, dark -> 0 (inverse-ish by using low thresh + binary)
        _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = gray.shape
        image_area = h * w
        if contours:
            largest = max(contours, key=cv2.contourArea)
            contour_area = float(cv2.contourArea(largest))
            ratio = contour_area / image_area if image_area else 0
            has_border = ratio < self.area_threshold
        else:
            contour_area = 0.0
            ratio = 0.0
            has_border = False

        # Fallback heuristic for thin borders: compare border band darkness vs center.
        band = max(5, min(h, w)//70)  # adaptive band height
        top = gray[:band, :]
        bottom = gray[-band:, :]
        left = gray[:, :band]
        right = gray[:, -band:]
        # Focus only on true edge rows/cols (avoid mixing interior by narrowing to band//2 near outer edge)
        def narrow_strip(strip, axis=0):
            if strip.shape[axis] > 3:
                if axis == 0:
                    return strip[: strip.shape[0]//2, :]
                else:
                    return strip[:, : strip.shape[1]//2]
            return strip
        top_n = narrow_strip(top, 0)
        bottom_n = narrow_strip(bottom, 0)
        left_n = narrow_strip(left, 1)
        right_n = narrow_strip(right, 1)
        border_pixels = np.concatenate([
            top_n.flatten(), bottom_n.flatten(), left_n.flatten(), right_n.flatten()
        ])
        center_region = gray[band:-band, band:-band] if h > 2*band and w > 2*band else gray
        border_mean = float(border_pixels.mean()) if border_pixels.size else 255.0
        center_mean = float(center_region.mean()) if center_region.size else 255.0
        # Dark fraction heuristic
        dark_fraction = float(np.mean(border_pixels < 60)) if border_pixels.size else 0.0
        contrast = center_mean - border_mean
        thin_border_detected = (contrast > 20 and dark_fraction > 0.15) or dark_fraction > 0.35

        final_has_border = has_border or thin_border_detected
        return final_has_border, {
            "image_area": image_area,
            "contour_area": contour_area,
            "area_ratio": ratio,
            "has_border_contour": has_border,
            "border_mean": border_mean,
            "center_mean": center_mean,
            "contrast": contrast,
            "thin_border_detected": thin_border_detected,
            "dark_fraction": dark_fraction,
        }

    def process(self, image, detect_meta: Dict[str, Any]):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return image, {"applied": False, "reason": "no_contours"}
        largest = max(contours, key=cv2.contourArea)
        mask = np.zeros_like(gray)
        cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)
        border_mask = cv2.bitwise_not(mask)
        output = image.copy()
        # Paint border white
        output[border_mask == 255] = (255, 255, 255)
        # Provide stats
        border_pixels = int(np.count_nonzero(border_mask))
        return output, {
            "applied": True,
            "border_pixels_masked": border_pixels,
            "area_ratio": detect_meta.get("area_ratio"),
        }

__all__ = ["EdgeMaskModule"]
