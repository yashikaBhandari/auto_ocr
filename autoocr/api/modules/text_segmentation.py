"""Text Segmentation Module: Line, Word, and Character Segmentation.

Splits text into separate lines, words, and characters for advanced OCR processing.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any, List
import cv2
import numpy as np
from .base_module import BaseModule


class TextSegmentationModule(BaseModule):
    """Segments text into lines, words, and characters."""

    name = "text_segmentation"

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect if text segmentation is applicable."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Check if image contains text (has high contrast areas)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        text_pixels = np.sum(binary == 0)  # Black pixels = text
        text_ratio = text_pixels / (binary.shape[0] * binary.shape[1])

        has_text = bool(0.05 < text_ratio < 0.95)  # Reasonable amount of text

        return has_text, {
            "text_ratio": float(round(text_ratio, 3)),
            "has_text": has_text,
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Perform text segmentation (creates metadata, returns segmented image)."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Step 1: Line Segmentation
        line_info = self._segment_lines(gray)

        # Step 2: Word Segmentation
        word_info = self._segment_words(gray)

        # Step 3: Character Segmentation
        char_info = self._segment_characters(gray)

        # Return original image (metadata in process_meta)
        result = image.copy()

        return result, {
            "line_count": len(line_info),
            "word_count": len(word_info),
            "character_count": len(char_info),
            "lines_detected": line_info,
            "words_detected": word_info,
            "characters_detected": char_info,
            "method": "Projection_Profile + Connected_Components"
        }

    def _segment_lines(self, gray) -> List[Dict[str, Any]]:
        """Segment text into lines using horizontal projection."""
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Horizontal projection
        horizontal_projection = np.sum(binary, axis=1)

        # Find line boundaries (non-zero regions)
        lines = []
        in_line = False
        line_start = 0

        for i, val in enumerate(horizontal_projection):
            if val > 0 and not in_line:
                line_start = i
                in_line = True
            elif val == 0 and in_line:
                lines.append({
                    "y_start": line_start,
                    "y_end": i,
                    "height": i - line_start,
                    "roi": binary[line_start:i, :]
                })
                in_line = False

        if in_line:
            lines.append({
                "y_start": line_start,
                "y_end": len(horizontal_projection),
                "height": len(horizontal_projection) - line_start,
                "roi": binary[line_start:, :]
            })

        return lines

    def _segment_words(self, gray) -> List[Dict[str, Any]]:
        """Segment text into words using vertical projection."""
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Vertical projection
        vertical_projection = np.sum(binary, axis=0)

        # Find word boundaries (non-zero regions)
        words = []
        in_word = False
        word_start = 0

        for i, val in enumerate(vertical_projection):
            if val > 0 and not in_word:
                word_start = i
                in_word = True
            elif val == 0 and in_word:
                words.append({
                    "x_start": word_start,
                    "x_end": i,
                    "width": i - word_start,
                    "roi": binary[:, word_start:i]
                })
                in_word = False

        if in_word:
            words.append({
                "x_start": word_start,
                "x_end": len(vertical_projection),
                "width": len(vertical_projection) - word_start,
                "roi": binary[:, word_start:]
            })

        return words

    def _segment_characters(self, gray) -> List[Dict[str, Any]]:
        """Segment individual characters using connected components."""
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Connected components
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

        characters = []

        for i in range(1, n_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]

            # Filter by area (avoid noise and large blobs)
            if 10 < area < 10000:
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                cx, cy = centroids[i]

                characters.append({
                    "label": i,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "area": area,
                    "center_x": round(cx, 2),
                    "center_y": round(cy, 2),
                    "roi": binary[y:y+h, x:x+w]
                })

        # Sort by position (left to right, top to bottom)
        characters.sort(key=lambda c: (c["y"], c["x"]))

        return characters


__all__ = ["TextSegmentationModule"]
