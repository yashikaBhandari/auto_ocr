"""Tests for security feature detection and removal modules."""
import pytest
import numpy as np
import cv2
from pathlib import Path

from autoocr.api.modules.guilloche_removal import GuillocheRemovalModule
from autoocr.api.modules.watermark_removal import WatermarkRemovalModule
from autoocr.api.modules.hologram_removal import HologramRemovalModule
from autoocr.api.modules.mrz_enhancement import MRZEnhancementModule
from autoocr.api.utils.security_detector import SecurityFeatureDetector
from autoocr.api.preprocessor import (
    DocumentPreprocessor,
    SecurityDocumentPreprocessor,
    OCROptimizedPreprocessor
)


@pytest.fixture
def sample_image():
    """Create a simple test image."""
    img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    # Add some text-like patterns
    cv2.rectangle(img, (100, 100), (700, 150), (0, 0, 0), -1)
    cv2.rectangle(img, (100, 200), (700, 250), (0, 0, 0), -1)
    return img


@pytest.fixture
def image_with_guilloche():
    """Create image with simulated guilloche pattern."""
    img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Add sinusoidal pattern (simplified guilloche)
    for i in range(0, 800, 5):
        y = int(500 + 50 * np.sin(i * 0.1))
        cv2.line(gray, (i, y-2), (i, y+2), 128, 1)

    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def image_with_watermark():
    """Create image with watermark."""
    img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Add watermark text
    cv2.putText(gray, "WATERMARK", (200, 500),
                cv2.FONT_HERSHEY_SIMPLEX, 3, 200, 2)

    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def image_with_mrz():
    """Create image with MRZ-like zone at bottom."""
    img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Add dense text at bottom (MRZ simulation)
    mrz_y = 900
    for i in range(5):
        cv2.putText(gray, "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<",
                   (50, mrz_y + i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1)

    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


class TestGuillocheRemoval:
    """Test guilloche pattern removal."""

    def test_detect_no_pattern(self, sample_image):
        module = GuillocheRemovalModule()
        should_process, meta = module.detect(sample_image)

        assert isinstance(should_process, bool)
        assert "pattern_strength" in meta
        assert "threshold" in meta

    def test_detect_pattern(self, image_with_guilloche):
        module = GuillocheRemovalModule(min_pattern_strength=0.10)
        should_process, meta = module.detect(image_with_guilloche)

        # Should detect the sinusoidal pattern
        assert "pattern_strength" in meta

    def test_process(self, image_with_guilloche):
        module = GuillocheRemovalModule()
        _, detect_meta = module.detect(image_with_guilloche)

        processed, process_meta = module.process(image_with_guilloche, detect_meta)

        assert processed.shape == image_with_guilloche.shape
        assert "frequencies_filtered" in process_meta


class TestWatermarkRemoval:
    """Test watermark removal."""

    def test_detect(self, image_with_watermark):
        module = WatermarkRemovalModule()
        should_process, meta = module.detect(image_with_watermark)

        assert isinstance(should_process, bool)
        assert "watermark_ratio" in meta

    def test_process(self, image_with_watermark):
        module = WatermarkRemovalModule()
        _, detect_meta = module.detect(image_with_watermark)

        processed, process_meta = module.process(image_with_watermark, detect_meta)

        assert processed.shape == image_with_watermark.shape
        assert "method" in process_meta
        assert process_meta["method"] == "morphological_subtraction"


class TestHologramRemoval:
    """Test hologram artifact removal."""

    def test_detect_no_hologram(self, sample_image):
        module = HologramRemovalModule()
        should_process, meta = module.detect(sample_image)

        assert isinstance(should_process, bool)
        assert "reflection_ratio" in meta

    def test_process(self, sample_image):
        module = HologramRemovalModule()
        _, detect_meta = module.detect(sample_image)

        processed, process_meta = module.process(sample_image, detect_meta)

        assert processed.shape == sample_image.shape
        assert "method" in process_meta


class TestMRZEnhancement:
    """Test MRZ enhancement."""

    def test_detect_no_mrz(self, sample_image):
        module = MRZEnhancementModule()
        has_mrz, meta = module.detect(sample_image)

        assert isinstance(has_mrz, bool)
        assert "text_density" in meta

    def test_detect_mrz(self, image_with_mrz):
        module = MRZEnhancementModule()
        has_mrz, meta = module.detect(image_with_mrz)

        # Should detect dense text at bottom
        assert "text_density" in meta
        assert meta["text_density"] > 0.20

    def test_process(self, image_with_mrz):
        module = MRZEnhancementModule()
        _, detect_meta = module.detect(image_with_mrz)

        processed, process_meta = module.process(image_with_mrz, detect_meta)

        assert processed.shape == image_with_mrz.shape
        assert "mrz_bbox" in process_meta


class TestSecurityDetector:
    """Test security feature detection."""

    def test_analyze_standard_document(self, sample_image, tmp_path):
        # Save temp image
        img_path = tmp_path / "test.png"
        cv2.imwrite(str(img_path), sample_image)

        detector = SecurityFeatureDetector()
        analysis = detector.analyze(str(img_path))

        assert "document_type" in analysis
        assert "features" in analysis
        assert "skew_angle" in analysis
        assert "risk_level" in analysis

    def test_classify_document_type(self, sample_image):
        detector = SecurityFeatureDetector()
        doc_type = detector._classify_document_type(sample_image)

        assert isinstance(doc_type, str)
        assert doc_type in ['passport', 'id_card', 'certificate', 'standard']


class TestPreprocessors:
    """Test main preprocessor classes."""

    def test_document_preprocessor(self, sample_image, tmp_path):
        input_path = tmp_path / "input.png"
        output_path = tmp_path / "output.png"
        cv2.imwrite(str(input_path), sample_image)

        preprocessor = DocumentPreprocessor()
        result = preprocessor.process_file(str(input_path), str(output_path))

        assert result['success']
        assert output_path.exists()

    def test_security_document_preprocessor(self, sample_image, tmp_path):
        input_path = tmp_path / "input.png"
        output_path = tmp_path / "output.png"
        cv2.imwrite(str(input_path), sample_image)

        preprocessor = SecurityDocumentPreprocessor()
        result = preprocessor.process_file(str(input_path), str(output_path))

        assert result['success']
        assert 'document_type' in result
        assert output_path.exists()

    def test_ocr_optimized_preprocessor(self, image_with_guilloche, tmp_path):
        input_path = tmp_path / "input.png"
        output_path = tmp_path / "output.png"
        cv2.imwrite(str(input_path), image_with_guilloche)

        preprocessor = OCROptimizedPreprocessor()
        result = preprocessor.process_file(str(input_path), str(output_path))

        assert result['success']
        assert output_path.exists()

    def test_batch_processing(self, sample_image, tmp_path):
        # Create input directory with multiple images
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        for i in range(3):
            cv2.imwrite(str(input_dir / f"test{i}.png"), sample_image)

        preprocessor = DocumentPreprocessor()
        results = preprocessor.process_batch(str(input_dir), str(output_dir))

        assert len(results) == 3
        assert all(r.get('success', False) for r in results)
        assert output_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
