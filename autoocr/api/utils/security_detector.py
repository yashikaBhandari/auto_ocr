"""Security Feature Detection and Document Classification.

Identifies document types and security features for appropriate processing.
"""
import cv2
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from ..utils.logging import get_logger

logger = get_logger("security_detector")


class SecurityFeatureDetector:
    """Detects security documents and identifies features that must be preserved or removed."""

    # ICAO 9303 passport background patterns, EU ID card Guilloche, etc.
    SECURITY_PATTERNS = {
        'passport': ['watermark', 'guilloche', 'machine_readable_zone'],
        'id_card': ['hologram_overlay', 'microtext', 'uv_printing'],
        'certificate': ['embossed_seal', 'background_pattern', 'signature'],
        'currency': ['security_thread', 'hologram', 'microprinting']
    }

    def __init__(self):
        """Initialize security feature detector."""
        pass

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """Detect document type and security features.

        Args:
            image_path: Path to image file

        Returns:
            Analysis results dictionary
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        return self.analyze_image(img)

    def analyze_image(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze image for document type and security features.

        Args:
            img: BGR image

        Returns:
            Analysis results dictionary
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        doc_type = self._classify_document_type(img)
        features = self._detect_security_features(img)
        skew_angle = self._calculate_skew(gray)
        risk_level = self._assess_processing_risk(img, doc_type)

        return {
            'document_type': doc_type,
            'features': features,
            'skew_angle': skew_angle,
            'risk_level': risk_level,
            'has_warp': self._detect_warp(gray)
        }

    def _classify_document_type(self, img: np.ndarray) -> str:
        """Classify document type based on visual signatures.

        Args:
            img: BGR image

        Returns:
            Document type string
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check for MRZ (Machine Readable Zone) = passport/ID
        if self._detect_mrz(gray):
            return 'passport'

        # Check for hologram reflections
        if self._detect_hologram(img):
            return 'id_card'

        # Check for certificate seals
        if self._detect_embossed_seal(gray):
            return 'certificate'

        return 'standard'

    def _detect_mrz(self, gray: np.ndarray) -> bool:
        """Detect Machine Readable Zone (MRZ).

        Args:
            gray: Grayscale image

        Returns:
            True if MRZ detected
        """
        height, width = gray.shape

        # MRZ is at bottom 10-15% of document
        search_height = int(height * 0.15)
        search_region = gray[-search_height:, :]

        # MRZ has very dense, regular text
        _, binary = cv2.threshold(search_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        text_density = np.count_nonzero(binary) / (search_region.shape[0] * search_region.shape[1])

        # MRZ typically has 40-70% text density
        return 0.30 < text_density < 0.80

    def _detect_hologram(self, img: np.ndarray) -> bool:
        """Detect hologram overlays.

        Args:
            img: BGR image

        Returns:
            True if hologram detected
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]

        # Holograms create low saturation + high value regions
        low_sat_bright = np.logical_and(s < 50, v > 200)
        ratio = np.count_nonzero(low_sat_bright) / (img.shape[0] * img.shape[1])

        return ratio > 0.05

    def _detect_embossed_seal(self, gray: np.ndarray) -> bool:
        """Detect embossed seals (certificates).

        Args:
            gray: Grayscale image

        Returns:
            True if embossed seal detected
        """
        # Embossed seals have distinctive 3D shadow patterns
        # Use Sobel to detect raised edges
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)

        # Look for circular high-gradient regions
        _, edges = cv2.threshold(gradient_magnitude.astype(np.uint8), 30, 255, cv2.THRESH_BINARY)
        circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, 1, 50,
                                   param1=50, param2=30, minRadius=30, maxRadius=200)

        return circles is not None and len(circles[0]) > 0

    def _detect_security_features(self, img: np.ndarray) -> List[str]:
        """Identify specific security features present.

        Args:
            img: BGR image

        Returns:
            List of detected feature names
        """
        features = []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Watermark detection (low-frequency patterns)
        if self._has_watermark(gray):
            features.append('watermark')

        # Microtext (high-frequency text patterns)
        if self._has_microtext(gray):
            features.append('microtext')

        # Guilloche patterns (complex curved lines)
        if self._has_guilloche(gray):
            features.append('guilloche')

        # Hologram (color-shifting reflections)
        if self._has_hologram(img):
            features.append('hologram')

        return features

    def _has_watermark(self, gray: np.ndarray) -> bool:
        """Check for watermark presence."""
        # Large morphological opening to extract background
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

        diff = cv2.absdiff(gray, background)
        watermark_ratio = np.count_nonzero(diff > 10) / (gray.shape[0] * gray.shape[1])

        return watermark_ratio > 0.20

    def _has_microtext(self, gray: np.ndarray) -> bool:
        """Check for microtext."""
        # Microtext shows up as very high frequency content
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()

        return variance > 150  # High edge variance indicates fine detail

    def _has_guilloche(self, gray: np.ndarray) -> bool:
        """Check for guilloche patterns."""
        # FFT analysis for repeating patterns
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        # Sample circular frequency bands
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2

        pattern_strength = 0.0
        for radius in range(30, 120, 10):
            y, x = np.ogrid[:rows, :cols]
            mask = ((x - ccol)**2 + (y - crow)**2 <= (radius + 5)**2) & \
                   ((x - ccol)**2 + (y - crow)**2 >= (radius - 5)**2)

            band_energy = np.sum(magnitude[mask])
            pattern_strength = max(pattern_strength, band_energy)

        total_energy = np.sum(magnitude)
        normalized_strength = pattern_strength / (total_energy + 1e-10)

        return normalized_strength > 0.15

    def _has_hologram(self, img: np.ndarray) -> bool:
        """Check for hologram overlay."""
        return self._detect_hologram(img)

    def _calculate_skew(self, gray: np.ndarray) -> float:
        """Calculate skew angle.

        Args:
            gray: Grayscale image

        Returns:
            Skew angle in degrees
        """
        try:
            from deskew import determine_skew
            return determine_skew(gray)
        except Exception as e:
            logger.warning(f"Skew detection failed: {e}")
            return 0.0

    def _detect_warp(self, gray: np.ndarray) -> bool:
        """Detect page warp/curve.

        Args:
            gray: Grayscale image

        Returns:
            True if warp detected
        """
        # Simple heuristic: detect curved text lines
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)

        if lines is None:
            return False

        # Check if lines are consistently non-horizontal (warped)
        non_horizontal = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if 5 < angle < 85:  # Not horizontal or vertical
                non_horizontal += 1

        return non_horizontal > len(lines) * 0.3

    def _assess_processing_risk(self, img: np.ndarray, doc_type: str) -> str:
        """Assess risk of processing this document type.

        Args:
            img: BGR image
            doc_type: Document type

        Returns:
            Risk level string
        """
        risk_levels = {
            'passport': 'high',
            'id_card': 'medium',
            'certificate': 'low',
            'currency': 'critical',
            'standard': 'low'
        }

        return risk_levels.get(doc_type, 'medium')
