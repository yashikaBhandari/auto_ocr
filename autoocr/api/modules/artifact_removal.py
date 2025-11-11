"""Artifact Removal Module: Fold Marks, Tape/Sticker, and Pattern Removal.

Removes:
- Fold or crease lines
- Tape marks and sticker artifacts
- Repeated patterns like stamps
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np
from .base_module import BaseModule


class ArtifactRemovalModule(BaseModule):
    """Removes folds, tape, and pattern artifacts."""

    name = "artifact_removal"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect fold marks, tape, and pattern artifacts."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Detect fold marks (lines)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=100, maxLineGap=20)
        fold_marks = lines is not None and len(lines) > 5

        # Detect tape/sticker (rectangular regions with distinct color/brightness)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        tape_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / (h + 1e-6)

            # Tape is often rectangular (high aspect ratio or low aspect ratio)
            if (100 < area < 100000) and (0.3 < aspect_ratio < 3.0 or aspect_ratio > 3 or aspect_ratio < 0.3):
                tape_count += 1

        # Detect repeated patterns using FFT
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)

        # Find peaks in frequency domain (indicates patterns)
        threshold = np.mean(magnitude) + np.std(magnitude)
        patterns = np.sum(magnitude > threshold * 2) / magnitude.size

        has_patterns = patterns > 0.01

        should_process = bool(fold_marks or tape_count > 1 or has_patterns)

        return should_process, {
            "fold_marks_detected": bool(fold_marks),
            "fold_mark_count": int(len(lines)) if lines is not None else 0,
            "tape_count": int(tape_count),
            "patterns_detected": bool(has_patterns),
            "pattern_ratio": float(round(patterns, 4)),
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Remove fold marks, tape, and patterns."""
        result = image.copy()
        gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY) if len(result.shape) == 3 else result

        # Step 1: Fold Mark Removal
        if detect_meta.get("fold_marks_detected"):
            result = self._remove_fold_marks(result, gray)

        # Step 2: Tape/Sticker Removal
        if detect_meta.get("tape_count", 0) > 1:
            result = self._remove_tape_sticker(result, gray)

        # Step 3: Pattern Suppression
        if detect_meta.get("patterns_detected"):
            result = self._suppress_patterns(result, gray)

        return result, {
            "fold_marks_removed": bool(detect_meta.get("fold_marks_detected", False)),
            "tape_removed": bool(detect_meta.get("tape_count", 0) > 1),
            "patterns_suppressed": bool(detect_meta.get("patterns_detected", False)),
            "method": "Hough_lines + Contours + FFT_filtering"
        }

    def _remove_fold_marks(self, image, gray):
        """Remove fold or crease lines."""
        # Detect lines
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=100, maxLineGap=20)

        # Create mask for lines
        fold_mask = np.zeros_like(gray)

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Draw thick line on mask
                cv2.line(fold_mask, (x1, y1), (x2, y2), 255, 5)

        # Dilate to capture full fold mark
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        fold_mask = cv2.dilate(fold_mask, kernel, iterations=2)

        # Inpaint
        if len(image.shape) == 3:
            result = cv2.inpaint(image, fold_mask, 3, cv2.INPAINT_TELEA)
        else:
            result = cv2.inpaint(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), fold_mask, 3, cv2.INPAINT_TELEA)

        return result

    def _remove_tape_sticker(self, image, gray):
        """Remove tape marks and sticker artifacts."""
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        tape_mask = np.zeros_like(gray)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / (h + 1e-6)

            # Tape is rectangular
            if (100 < area < 100000) and (0.3 < aspect_ratio < 3.0 or aspect_ratio > 3 or aspect_ratio < 0.3):
                cv2.drawContours(tape_mask, [cnt], 0, 255, -1)

        # Dilate
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        tape_mask = cv2.dilate(tape_mask, kernel, iterations=2)

        # Inpaint
        if len(image.shape) == 3:
            result = cv2.inpaint(image, tape_mask, 3, cv2.INPAINT_TELEA)
        else:
            result = cv2.inpaint(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), tape_mask, 3, cv2.INPAINT_TELEA)

        return result

    def _suppress_patterns(self, image, gray):
        """Suppress repeated patterns using FFT filtering."""
        # FFT
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)
        phase = np.angle(f_shift)

        # Create pattern suppression mask (attenuate high-frequency periodic components)
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2

        # Gaussian mask to suppress high frequencies
        x = np.arange(cols) - ccol
        y = np.arange(rows) - crow
        X, Y = np.meshgrid(x, y)
        D = np.sqrt(X**2 + Y**2)

        # Suppress patterns at specific frequencies
        sigma = max(rows, cols) // 20
        suppression_mask = 1 - 0.5 * np.exp(-(D**2) / (2 * (sigma**2)))

        # Apply suppression
        f_filtered = f_shift * suppression_mask

        # Inverse FFT
        f_ishift = np.fft.ifftshift(f_filtered)
        result_gray = np.fft.ifft2(f_ishift)
        result_gray = np.abs(result_gray)

        # Normalize
        result_gray = cv2.normalize(result_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # Convert back to BGR if needed
        if len(image.shape) == 3:
            result = cv2.cvtColor(result_gray, cv2.COLOR_GRAY2BGR)
        else:
            result = result_gray

        return result


__all__ = ["ArtifactRemovalModule"]
