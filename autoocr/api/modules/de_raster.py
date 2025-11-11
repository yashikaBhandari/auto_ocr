"""De-raster Module: Grid, Stamp, and Watermark Removal.

Removes structured artifacts:
- Grid lines and graph paper rulings
- Stamps, seals, and ink marks
- Light watermarks and background patterns
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np
from .base_module import BaseModule


class DeRasterModule(BaseModule):
    """Removes grids, stamps, and watermarks."""

    name = "de_raster"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect presence of grid lines, stamps, or watermarks."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Detect grid lines using Hough transform
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=10)
        grid_detected = lines is not None and len(lines) > 10

        # Detect stamps/seals (circular or large dark regions)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        stamp_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 500 < area < 50000:  # Typical stamp size
                stamp_count += 1

        # Detect watermarks using frequency analysis
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)

        # High energy in low frequencies indicates watermark/background
        low_freq_energy = np.sum(magnitude[:magnitude.shape[0]//4, :magnitude.shape[1]//4])
        total_energy = np.sum(magnitude)
        watermark_ratio = low_freq_energy / (total_energy + 1e-6)

        should_process = grid_detected or stamp_count > 2 or watermark_ratio > 0.3

        return should_process, {
            "grid_detected": grid_detected,
            "grid_line_count": len(lines) if lines is not None else 0,
            "stamp_count": stamp_count,
            "watermark_ratio": round(watermark_ratio, 3),
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Remove grids, stamps, and watermarks."""
        result = image.copy()
        gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY) if len(result.shape) == 3 else result

        # Step 1: Grid Line Removal
        if detect_meta.get("grid_detected"):
            result = self._remove_grid_lines(result, gray)

        # Step 2: Stamp Removal
        if detect_meta.get("stamp_count", 0) > 2:
            result = self._remove_stamps(result, gray)

        # Step 3: Watermark Removal
        if detect_meta.get("watermark_ratio", 0) > 0.3:
            result = self._remove_watermark(result)

        return result, {
            "grid_removed": detect_meta.get("grid_detected", False),
            "stamps_removed": detect_meta.get("stamp_count", 0) > 2,
            "watermark_removed": detect_meta.get("watermark_ratio", 0) > 0.3,
            "method": "Hough_lines + Contour + FFT"
        }

    def _remove_grid_lines(self, image, gray):
        """Remove horizontal and vertical grid lines."""
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Horizontal kernel for horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        horizontal_mask = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)

        # Vertical kernel for vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
        vertical_mask = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)

        # Combine masks
        grid_mask = cv2.bitwise_or(horizontal_mask, vertical_mask)

        # Inpaint to remove grid
        result = cv2.inpaint(image, grid_mask, 3, cv2.INPAINT_TELEA)
        return result

    def _remove_stamps(self, image, gray):
        """Remove stamps and seals using contour detection."""
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        stamp_mask = np.zeros_like(gray)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 500 < area < 50000:
                cv2.drawContours(stamp_mask, [cnt], 0, 255, -1)

        # Dilate mask slightly to capture full stamp
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        stamp_mask = cv2.dilate(stamp_mask, kernel, iterations=2)

        # Inpaint
        result = cv2.inpaint(image, stamp_mask, 3, cv2.INPAINT_TELEA)
        return result

    def _remove_watermark(self, image):
        """Remove watermarks using frequency domain filtering."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # FFT
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)

        # Create high-pass filter to suppress low-frequency watermarks
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2

        # Gaussian high-pass filter
        x = np.arange(cols) - ccol
        y = np.arange(rows) - crow
        X, Y = np.meshgrid(x, y)
        D = np.sqrt(X**2 + Y**2)

        # High-pass filter (suppress low frequencies)
        sigma = max(rows, cols) // 6
        high_pass = 1 - np.exp(-(D**2) / (2 * (sigma**2)))

        # Apply filter
        f_filtered = f_shift * high_pass

        # Inverse FFT
        f_ishift = np.fft.ifftshift(f_filtered)
        result_gray = np.fft.ifft2(f_ishift)
        result_gray = np.abs(result_gray)

        # Normalize and convert back
        result_gray = cv2.normalize(result_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # Convert back to BGR if needed
        if len(image.shape) == 3:
            result = cv2.cvtColor(result_gray, cv2.COLOR_GRAY2BGR)
        else:
            result = result_gray

        return result


__all__ = ["DeRasterModule"]
