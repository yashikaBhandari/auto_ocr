"""Watermark Removal Module.

Removes semi-transparent watermarks and background patterns that interfere with OCR.
Uses morphological operations and LAB color space for better separation.
"""
import cv2
import numpy as np
from typing import Tuple, Dict, Any
from .base_module import BaseModule


class WatermarkRemovalModule(BaseModule):
    """Removes watermarks and background patterns."""

    name = "watermark_removal"

    def __init__(self, min_watermark_ratio: float = 0.20):
        """Initialize watermark removal module.

        Args:
            min_watermark_ratio: Minimum ratio of low-frequency content to trigger
        """
        self.min_watermark_ratio = min_watermark_ratio

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect presence of watermark patterns.

        Args:
            image: BGR image

        Returns:
            (should_process, metadata) tuple
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Estimate background/watermark using large morphological opening
        kernel_size = max(15, min(gray.shape) // 50)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        background_estimate = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

        # Calculate difference between original and background
        diff = cv2.absdiff(gray, background_estimate)

        # Measure how much of the image is "background pattern"
        watermark_pixels = np.count_nonzero(diff > 10)
        total_pixels = gray.shape[0] * gray.shape[1]
        watermark_ratio = watermark_pixels / total_pixels

        should_process = watermark_ratio > self.min_watermark_ratio

        return should_process, {
            "watermark_ratio": float(watermark_ratio),
            "watermark_pixels": int(watermark_pixels),
            "threshold": self.min_watermark_ratio
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Remove watermark by estimating and subtracting background pattern.

        Args:
            image: BGR image
            detect_meta: Detection metadata

        Returns:
            (processed_image, process_metadata) tuple
        """
        is_color = len(image.shape) == 3

        if is_color:
            # Convert to LAB color space for better separation
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
        else:
            l = image.copy()

        # Estimate watermark pattern via morphological opening
        kernel_size = max(15, min(l.shape) // 50)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        watermark_estimation = cv2.morphologyEx(l, cv2.MORPH_OPEN, kernel)

        # Subtract watermark (careful not to underflow)
        l_clean = cv2.subtract(l, watermark_estimation // 2)  # Divide by 2 to be conservative

        # Apply CLAHE to boost text contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_clean)

        # Convert back to BGR if input was color
        if is_color:
            lab_final = cv2.merge([l_enhanced, a, b])
            result = cv2.cvtColor(lab_final, cv2.COLOR_LAB2BGR)
        else:
            result = l_enhanced

        return result, {
            "watermark_ratio": detect_meta["watermark_ratio"],
            "method": "morphological_subtraction",
            "contrast_enhanced": True
        }
