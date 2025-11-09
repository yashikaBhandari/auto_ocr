"""Hologram Artifact Removal Module.

Removes hologram reflections and artifacts that create bright spots, blur,
and distortion in security documents.
"""
import cv2
import numpy as np
from typing import Tuple, Dict, Any
from .base_module import BaseModule


class HologramRemovalModule(BaseModule):
    """Removes hologram reflections and artifacts."""

    name = "hologram_removal"

    def __init__(self, reflection_threshold: int = 200):
        """Initialize hologram removal module.

        Args:
            reflection_threshold: Brightness threshold for detecting reflections
        """
        self.reflection_threshold = reflection_threshold

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect presence of hologram reflections.

        Args:
            image: BGR image

        Returns:
            (should_process, metadata) tuple
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Detect very bright regions (typical of hologram reflections)
        _, bright_mask = cv2.threshold(gray, self.reflection_threshold, 255, cv2.THRESH_BINARY)

        # Count reflection pixels
        reflection_pixels = np.count_nonzero(bright_mask)
        total_pixels = gray.shape[0] * gray.shape[1]
        reflection_ratio = reflection_pixels / total_pixels

        # Also check for low saturation in bright areas (holograms often desaturate)
        if len(image.shape) == 3:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            s = hsv[:, :, 1]
            v = hsv[:, :, 2]

            # Low saturation + high value = likely reflection
            low_sat_bright = np.logical_and(s < 50, v > self.reflection_threshold)
            desaturated_ratio = np.count_nonzero(low_sat_bright) / total_pixels
        else:
            desaturated_ratio = 0.0

        # Trigger if we have significant reflections or desaturated bright areas
        should_process = reflection_ratio > 0.02 or desaturated_ratio > 0.05

        return should_process, {
            "reflection_ratio": float(reflection_ratio),
            "desaturated_bright_ratio": float(desaturated_ratio),
            "reflection_pixels": int(reflection_pixels)
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Remove hologram reflections using inpainting.

        Args:
            image: BGR image
            detect_meta: Detection metadata

        Returns:
            (processed_image, process_metadata) tuple
        """
        is_color = len(image.shape) == 3
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if is_color else image

        # Create reflection mask
        if is_color:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            s = hsv[:, :, 1]
            v = hsv[:, :, 2]

            # Reflection areas: low saturation but high value
            reflection_mask = np.logical_and(s < 50, v > self.reflection_threshold).astype(np.uint8) * 255
        else:
            _, reflection_mask = cv2.threshold(gray, self.reflection_threshold, 255, cv2.THRESH_BINARY)

        # Dilate mask slightly to cover reflection edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        reflection_mask = cv2.dilate(reflection_mask, kernel, iterations=2)

        # Inpaint reflection areas
        if np.count_nonzero(reflection_mask) > 0:
            result = cv2.inpaint(image, reflection_mask, 5, cv2.INPAINT_TELEA)

            # Additional sharpening in inpainted zones to match surrounding text
            blurred = cv2.GaussianBlur(result, (0, 0), 3)
            sharpened = cv2.addWeighted(result, 1.5, blurred, -0.5, 0)

            # Only apply sharpening where we inpainted
            result = np.where(reflection_mask[:, :, None] > 0 if is_color else reflection_mask > 0,
                            sharpened, result)
        else:
            result = image.copy()

        return result, {
            "reflection_ratio": detect_meta["reflection_ratio"],
            "inpainted_pixels": int(np.count_nonzero(reflection_mask)),
            "method": "telea_inpainting"
        }
