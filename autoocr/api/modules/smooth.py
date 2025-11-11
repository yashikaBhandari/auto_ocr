"""Smooth Module: Gaussian, Median, and Bilateral Smoothing.

Reduces noise while preserving edges and important details.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np
from .base_module import BaseModule


class SmoothModule(BaseModule):
    """Applies various smoothing techniques."""

    name = "smooth"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect if smoothing is needed (grainy images)."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Measure graininess using gradient magnitude
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        graininess = np.mean(magnitude)

        # High gradient = grainy
        is_grainy = graininess > 20

        return is_grainy, {
            "graininess": round(graininess, 2),
            "is_grainy": is_grainy,
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Apply smoothing using multiple techniques."""
        result = image.copy()
        graininess = detect_meta.get("graininess", 0)

        # Determine smoothing strength based on graininess
        if graininess > 40:  # Very grainy
            result = self._gaussian_smoothing(result, strength="strong")
            result = self._median_smoothing(result, kernel_size=5)
            result = self._bilateral_smoothing(result, strength="strong")
        elif graininess > 25:  # Moderately grainy
            result = self._gaussian_smoothing(result, strength="medium")
            result = self._bilateral_smoothing(result, strength="medium")
        else:  # Slightly grainy
            result = self._median_smoothing(result, kernel_size=3)
            result = self._bilateral_smoothing(result, strength="light")

        return result, {
            "gaussian_applied": True,
            "median_applied": True,
            "bilateral_applied": True,
            "graininess_input": graininess,
            "method": "Gaussian + Median + Bilateral"
        }

    def _gaussian_smoothing(self, image, strength="medium"):
        """Reduce grain using Gaussian blur."""
        if strength == "strong":
            kernel_size = 5
            sigma = 1.5
        elif strength == "medium":
            kernel_size = 3
            sigma = 1.0
        else:  # light
            kernel_size = 3
            sigma = 0.5

        result = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
        return result

    def _median_smoothing(self, image, kernel_size=3):
        """Remove impulse noise while preserving edges."""
        if len(image.shape) == 3:
            # Apply to each channel
            b, g, r = cv2.split(image)
            b = cv2.medianBlur(b, kernel_size)
            g = cv2.medianBlur(g, kernel_size)
            r = cv2.medianBlur(r, kernel_size)
            result = cv2.merge([b, g, r])
        else:
            result = cv2.medianBlur(image, kernel_size)

        return result

    def _bilateral_smoothing(self, image, strength="medium"):
        """Smooth regions while keeping edges crisp (edge-preserving)."""
        if strength == "strong":
            diameter = 15
            sigma_color = 80
            sigma_space = 80
        elif strength == "medium":
            diameter = 9
            sigma_color = 75
            sigma_space = 75
        else:  # light
            diameter = 9
            sigma_color = 50
            sigma_space = 50

        if len(image.shape) == 3:
            result = cv2.bilateralFilter(image, diameter, sigma_color, sigma_space)
        else:
            # Convert to BGR for bilateral filter
            temp = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            result = cv2.bilateralFilter(temp, diameter, sigma_color, sigma_space)
            result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

        return result


__all__ = ["SmoothModule"]
