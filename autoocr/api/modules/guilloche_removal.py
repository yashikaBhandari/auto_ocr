"""Guilloche Pattern Removal Module.

Removes repeating curved patterns (guilloche) commonly found in security documents
using frequency domain filtering. These patterns interfere with OCR but can be
removed while preserving text.
"""
import cv2
import numpy as np
from typing import Tuple, Dict, Any
from .base_module import BaseModule


class GuillocheRemovalModule(BaseModule):
    """Removes guilloche patterns using FFT filtering."""

    name = "guilloche_removal"

    def __init__(self, min_pattern_strength: float = 0.15):
        """Initialize guilloche removal module.

        Args:
            min_pattern_strength: Minimum pattern strength to trigger removal
        """
        self.min_pattern_strength = min_pattern_strength

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        """Detect presence of guilloche patterns using frequency analysis.

        Args:
            image: BGR image

        Returns:
            (should_process, metadata) tuple
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Perform FFT
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = np.abs(fshift)

        # Analyze frequency distribution
        # Guilloche patterns show up as circular/radial patterns in frequency domain
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2

        # Sample circular frequency bands (guilloche typical range)
        pattern_strength = 0.0
        for radius in range(30, 120, 10):
            # Create circular mask
            y, x = np.ogrid[:rows, :cols]
            mask = ((x - ccol)**2 + (y - crow)**2 <= (radius + 5)**2) & \
                   ((x - ccol)**2 + (y - crow)**2 >= (radius - 5)**2)

            # Measure energy in this band
            band_energy = np.sum(magnitude_spectrum[mask])
            pattern_strength = max(pattern_strength, band_energy)

        # Normalize
        total_energy = np.sum(magnitude_spectrum)
        pattern_strength = pattern_strength / (total_energy + 1e-10)

        should_process = pattern_strength > self.min_pattern_strength

        return should_process, {
            "pattern_strength": float(pattern_strength),
            "threshold": self.min_pattern_strength
        }

    def process(self, image, detect_meta: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Remove guilloche patterns using FFT filtering.

        Args:
            image: BGR image
            detect_meta: Detection metadata

        Returns:
            (processed_image, process_metadata) tuple
        """
        is_color = len(image.shape) == 3
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if is_color else image

        # Perform 2D FFT
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)

        # Create filter mask
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2
        mask = np.ones((rows, cols), np.uint8)

        # Block specific frequency bands where guilloche patterns appear
        for radius in range(30, 120):
            cv2.circle(mask, (ccol, crow), radius, 0, 1)

        # Apply mask
        fshift_filtered = fshift * mask

        # Inverse FFT
        f_ishift = np.fft.ifftshift(fshift_filtered)
        img_back = np.fft.ifft2(f_ishift)
        img_back = np.real(img_back)

        # Normalize to 0-255
        img_back = cv2.normalize(img_back, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        # Sharpen text that was slightly weakened by filtering
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        img_sharpened = cv2.filter2D(img_back, -1, kernel)

        # Convert back to color if input was color
        if is_color:
            result = cv2.cvtColor(img_sharpened, cv2.COLOR_GRAY2BGR)
        else:
            result = img_sharpened

        return result, {
            "pattern_strength": detect_meta["pattern_strength"],
            "frequencies_filtered": "30-120px radius"
        }
