"""Sharpen Module: Edge Enhancement and Detail Refinement.

Increases clarity of characters and highlights fine details without introducing noise.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np
from .base_module import BaseModule


class SharpenModule(BaseModule):
    """Sharpens edges and refines details."""

    name = "sharpen"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect if sharpening is needed (blurry images)."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Laplacian variance indicates blurriness
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # Low variance = blurry
        is_blurry = bool(laplacian_var < 100)

        return is_blurry, {
            "laplacian_variance": float(round(laplacian_var, 2)),
            "is_blurry": is_blurry,
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Apply edge enhancement and detail refinement."""
        result = image.copy()

        # Step 1: Edge Enhancement
        result = self._enhance_edges(result)

        # Step 2: Detail Refinement
        result = self._refine_details(result)

        return result, {
            "edge_enhanced": True,
            "details_refined": True,
            "laplacian_variance_input": detect_meta.get("laplacian_variance", 0),
            "method": "Unsharp_Mask + High_Pass"
        }

    def _enhance_edges(self, image):
        """Enhance edges using unsharp masking."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            color_image = image
        else:
            gray = image
            color_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        # Unsharp masking: image + (image - blurred) * strength
        blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)

        # Subtract blurred from original to get edges
        edges = cv2.subtract(gray, blurred)

        # Add edges back to original
        sharpened = cv2.addWeighted(gray, 1.0, edges, 0.8, 0)

        # Convert back to BGR if needed
        if len(image.shape) == 3:
            result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        else:
            result = sharpened

        return result

    def _refine_details(self, image):
        """Refine details using high-pass filtering."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            result_img = image.copy()
        else:
            gray = image
            result_img = image.copy()

        # High-pass filter
        # Subtract low-pass (blurred) from original
        low_pass = cv2.GaussianBlur(gray, (5, 5), 1)
        high_pass = cv2.subtract(gray, low_pass)

        # Convert to float for processing
        high_pass_float = high_pass.astype(np.float32) / 255.0
        gray_float = gray.astype(np.float32) / 255.0

        # Add high-pass details back
        detailed = gray_float + high_pass_float * 0.5
        detailed = np.clip(detailed, 0, 1)
        detailed = (detailed * 255).astype(np.uint8)

        # Convert back to BGR if needed
        if len(image.shape) == 3:
            result = cv2.cvtColor(detailed, cv2.COLOR_GRAY2BGR)
        else:
            result = detailed

        return result


__all__ = ["SharpenModule"]
