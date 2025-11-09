"""MRZ (Machine Readable Zone) Enhancement Module.

Specialized processing for MRZ zones in passports and ID cards.
Maximizes OCR readability while preserving MRZ integrity.
"""
import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional
from .base_module import BaseModule


class MRZEnhancementModule(BaseModule):
    """Enhances MRZ zones for maximum OCR accuracy."""

    name = "mrz_enhancement"

    def __init__(self):
        """Initialize MRZ enhancement module."""
        pass

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect if image contains an MRZ zone.

        MRZ is typically at the bottom of document, contains dense text,
        and has specific aspect ratio.

        Args:
            image: BGR image

        Returns:
            (should_process, metadata) tuple
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        height, width = gray.shape

        # MRZ is always at bottom, typically bottom 10-15%
        search_height = int(height * 0.15)
        search_region = gray[-search_height:, :]

        # MRZ has very dense text - check text density
        # Apply threshold to get text
        _, binary = cv2.threshold(search_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Calculate text density
        text_pixels = np.count_nonzero(binary)
        region_pixels = search_region.shape[0] * search_region.shape[1]
        text_density = text_pixels / region_pixels

        # MRZ typically has 40-70% text density and horizontal lines
        has_mrz = text_density > 0.30 and text_density < 0.80

        mrz_bbox = None
        if has_mrz:
            # Find exact MRZ bounding box
            mrz_bbox = self._find_mrz_bbox(gray)
            has_mrz = mrz_bbox is not None

        return has_mrz, {
            "text_density": float(text_density),
            "mrz_bbox": mrz_bbox,
            "search_region_height": search_height
        }

    def _find_mrz_bbox(self, gray: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Find exact bounding box of MRZ zone.

        Args:
            gray: Grayscale image

        Returns:
            (x, y, w, h) or None if not found
        """
        height, width = gray.shape
        search_height = int(height * 0.20)
        search_region = gray[-search_height:, :]

        # Apply threshold
        _, binary = cv2.threshold(search_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Find largest horizontal contour (MRZ text block)
        best_contour = None
        best_area = 0

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            # MRZ is wide and relatively short
            if w > width * 0.6 and h < search_height * 0.5 and area > best_area:
                best_contour = (x, y + (height - search_height), w, h)
                best_area = area

        return best_contour

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Enhance MRZ zone for OCR.

        Args:
            image: BGR image
            detect_meta: Detection metadata

        Returns:
            (processed_image, process_metadata) tuple
        """
        is_color = len(image.shape) == 3
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if is_color else image

        height, width = gray.shape
        mrz_bbox = detect_meta.get("mrz_bbox")

        if mrz_bbox is None:
            # Fallback to bottom region
            mrz_height = int(height * 0.12)
            x, y, w, h = 0, height - mrz_height, width, mrz_height
        else:
            x, y, w, h = mrz_bbox

        # Extract MRZ region
        mrz_region = gray[y:y+h, x:x+w].copy()

        # Remove any horizontal baseline lines
        mrz_clean = self._remove_mrz_baseline(mrz_region)

        # Super-sharpen MRZ
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        mrz_sharp = cv2.filter2D(mrz_clean, -1, kernel)

        # Binarize MRZ only (Otsu)
        _, mrz_binary = cv2.threshold(mrz_sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Create result image
        result = image.copy()

        # Replace MRZ region with enhanced version
        if is_color:
            mrz_color = cv2.cvtColor(mrz_binary, cv2.COLOR_GRAY2BGR)
            result[y:y+h, x:x+w] = mrz_color
        else:
            result[y:y+h, x:x+w] = mrz_binary

        return result, {
            "mrz_bbox": (x, y, w, h),
            "method": "targeted_binarization",
            "baseline_removed": True
        }

    def _remove_mrz_baseline(self, mrz_region: np.ndarray) -> np.ndarray:
        """Remove horizontal baseline that can confuse OCR.

        Args:
            mrz_region: MRZ region in grayscale

        Returns:
            Cleaned MRZ region
        """
        # Use horizontal projection to find baseline
        projection = np.sum(mrz_region == 0, axis=1)  # Count dark pixels per row

        if len(projection) == 0:
            return mrz_region

        # Find rows with abnormally high dark pixel counts (baselines)
        mean_proj = np.mean(projection)
        std_proj = np.std(projection)

        baseline_threshold = mean_proj + 2 * std_proj

        # Remove baseline rows
        result = mrz_region.copy()
        for i, count in enumerate(projection):
            if count > baseline_threshold:
                # Fill this row with white
                result[i, :] = 255

        return result
