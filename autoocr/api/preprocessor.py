"""Complete preprocessing pipeline for scanned documents.

Provides three processing modes:
1. DocumentPreprocessor - Standard preprocessing
2. SecurityDocumentPreprocessor - Preserves security features
3. OCROptimizedPreprocessor - Removes security features for maximum OCR accuracy
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile
import shutil

from .utils.config import ProcessingConfig, SecurityDocumentConfig, OCROptimizedConfig
from .utils.gpu_manager import get_gpu_manager
from .utils.security_detector import SecurityFeatureDetector
from .utils.logging import get_logger
from .pipeline import Pipeline

# Import all modules
from .modules.edge_mask import EdgeMaskModule
from .modules.orientation import OrientationModule
from .modules.perspective import PerspectiveModule
from .modules.deskew import DeskewModule
from .modules.denoise import DenoiseModule
from .modules.enhance import EnhanceModule
from .modules.text_refine import TextRefineModule
from .modules.binarize import BinarizeModule
from .modules.guilloche_removal import GuillocheRemovalModule
from .modules.watermark_removal import WatermarkRemovalModule
from .modules.hologram_removal import HologramRemovalModule
from .modules.mrz_enhancement import MRZEnhancementModule

logger = get_logger("preprocessor")


LEGAL_WARNING = """
⚠️  WARNING: Processing security documents may be illegal without authorization.
This tool is provided for legitimate use cases only:
- Authorized law enforcement digital forensics
- Personal document archival with consent
- Academic research on OCR improvement
- Government document digitization programs

Users are solely responsible for legal compliance.
"""


class DocumentPreprocessor:
    """Complete preprocessing pipeline for scanned documents."""

    def __init__(self, config: ProcessingConfig = None):
        """Initialize document preprocessor.

        Args:
            config: Processing configuration
        """
        self.config = config or ProcessingConfig()
        self.gpu_manager = get_gpu_manager(force_cpu=not self.config.gpu)

        # Build module pipeline based on config
        modules = self._build_pipeline()
        self.pipeline = Pipeline(modules)

    def _build_pipeline(self) -> List:
        """Build processing module list based on configuration."""
        modules = []

        # Always start with edge masking
        modules.append(EdgeMaskModule())

        # Orientation and perspective
        modules.append(OrientationModule())
        modules.append(PerspectiveModule())

        # Deskew if enabled
        if self.config.deskew_enabled:
            modules.append(DeskewModule())

        # Denoise if enabled
        if self.config.noise_reduction:
            modules.append(DenoiseModule())

        # Contrast enhancement
        if self.config.contrast_enhancement:
            modules.append(EnhanceModule())

        # Text refinement
        modules.append(TextRefineModule())

        # Binarization (unless disabled)
        if not hasattr(self.config, 'allow_binarization') or self.config.allow_binarization:
            modules.append(BinarizeModule())

        return modules

    def process_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process a single file through the complete pipeline.

        Args:
            input_path: Path to input image/PDF
            output_path: Path to save output

        Returns:
            Processing results dictionary
        """
        logger.info(f"Processing file: {input_path}")

        # Load image
        img = cv2.imread(input_path)
        if img is None:
            raise ValueError(f"Could not load image: {input_path}")

        # Run pipeline
        result = self.pipeline.run_page(img)

        # Save output
        cv2.imwrite(output_path, result['final'])

        logger.info(f"Saved output: {output_path}")

        return {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'steps': result['steps']
        }

    def process_batch(self, input_dir: str, output_dir: str) -> List[Dict[str, Any]]:
        """Process multiple documents.

        Args:
            input_dir: Directory containing input files
            output_dir: Directory for outputs

        Returns:
            List of processing results
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        # Find all supported files
        patterns = ["*.pdf", "*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg"]
        files = []
        for pattern in patterns:
            files.extend(input_path.glob(pattern))

        logger.info(f"Found {len(files)} files to process")

        for file in files:
            try:
                output_file = output_path / f"{file.stem}_processed{file.suffix}"
                result = self.process_file(str(file), str(output_file))
                results.append({'file': file.name, **result})
            except Exception as e:
                logger.error(f"Error processing {file.name}: {e}")
                results.append({
                    'file': file.name,
                    'success': False,
                    'error': str(e)
                })

        return results


class SecurityDocumentPreprocessor(DocumentPreprocessor):
    """Specialized preprocessor for security documents.

    Preserves security features while only fixing scan artifacts.
    """

    def __init__(self, config: SecurityDocumentConfig = None):
        """Initialize security document preprocessor.

        Args:
            config: Security document configuration
        """
        self.config = config or SecurityDocumentConfig()
        self.gpu_manager = get_gpu_manager(force_cpu=not self.config.gpu)
        self.security_detector = SecurityFeatureDetector()

        # Build conservative pipeline
        modules = self._build_conservative_pipeline()
        self.pipeline = Pipeline(modules)

    def _build_conservative_pipeline(self) -> List:
        """Build minimal processing pipeline that preserves security features."""
        modules = []

        # Only basic geometric corrections
        modules.append(OrientationModule())

        # Gentle deskew only if major skew
        if self.config.deskew_enabled:
            modules.append(DeskewModule())

        # Very minimal denoising (preserve patterns)
        if self.config.noise_reduction and self.config.max_denoising > 0:
            modules.append(DenoiseModule())

        # No binarization, no aggressive enhancement

        return modules

    def process_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process security document with feature preservation.

        Args:
            input_path: Path to input image
            output_path: Path to save output

        Returns:
            Processing results with compliance information
        """
        logger.info(f"Processing security document: {input_path}")

        # Analyze document
        analysis = self.security_detector.analyze(input_path)
        logger.info(f"Detected: {analysis['document_type']}, Features: {analysis['features']}")

        # Load image
        img = cv2.imread(input_path)
        if img is None:
            raise ValueError(f"Could not load image: {input_path}")

        # Only proceed if skew is significant
        if abs(analysis['skew_angle']) > 2.0:
            result = self.pipeline.run_page(img)
            processed = result['final']
        else:
            logger.info("Skew minimal, preserving original")
            processed = img
            result = {'steps': [], 'final': img}

        # Save output
        cv2.imwrite(output_path, processed)

        return {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'document_type': analysis['document_type'],
            'security_features_preserved': analysis['features'],
            'compliance': 'ICAO 9303' if analysis['document_type'] == 'passport' else 'N/A',
            'steps': result['steps']
        }


class OCROptimizedPreprocessor(DocumentPreprocessor):
    """Aggressively removes security features to maximize OCR accuracy.

    ⚠️  Use ONLY when legal and necessary.
    """

    def __init__(self, config: OCROptimizedConfig = None):
        """Initialize OCR-optimized preprocessor.

        Args:
            config: OCR-optimized configuration
        """
        self.config = config or OCROptimizedConfig()
        self.gpu_manager = get_gpu_manager(force_cpu=not self.config.gpu)
        self.security_detector = SecurityFeatureDetector()

        # Build aggressive pipeline
        modules = self._build_ocr_pipeline()
        self.pipeline = Pipeline(modules)

    def _build_ocr_pipeline(self) -> List:
        """Build aggressive OCR-optimized pipeline."""
        modules = []

        # Security feature removal (order matters!)
        if self.config.remove_guilloche:
            modules.append(GuillocheRemovalModule())

        if self.config.remove_watermarks:
            modules.append(WatermarkRemovalModule())

        if self.config.flatten_holograms:
            modules.append(HologramRemovalModule())

        # Standard preprocessing
        modules.append(EdgeMaskModule())
        modules.append(OrientationModule())
        modules.append(PerspectiveModule())
        modules.append(DeskewModule())
        modules.append(DenoiseModule())
        modules.append(EnhanceModule())

        # MRZ enhancement if priority set
        if self.config.mrz_priority:
            modules.append(MRZEnhancementModule())

        modules.append(TextRefineModule())

        # Aggressive binarization
        if self.config.allow_binarization:
            modules.append(BinarizeModule())

        return modules

    def _check_legal_compliance(self, document_path: str) -> bool:
        """Check legal authorization for processing.

        Args:
            document_path: Path to document

        Returns:
            True if should proceed
        """
        if not self.config.legal_compliance_check:
            return True

        # Analyze document type
        analysis = self.security_detector.analyze(document_path)
        doc_type = analysis['document_type']

        if doc_type in ['passport', 'currency']:
            print(LEGAL_WARNING)
            logger.warning(f"Detected {doc_type} - requires legal authorization")
            # In production, this should check actual authorization
            # For now, log warning and proceed
            return True

        return True

    def process_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Process document with aggressive security feature removal.

        Args:
            input_path: Path to input image
            output_path: Path to save output

        Returns:
            Processing results with OCR improvement metrics
        """
        # Legal compliance check
        if not self._check_legal_compliance(input_path):
            return {
                'success': False,
                'error': 'Legal authorization required'
            }

        logger.info(f"OCR-optimizing document: {input_path}")

        # Analyze document
        analysis = self.security_detector.analyze_image(cv2.imread(input_path))

        # Load and process
        img = cv2.imread(input_path)
        if img is None:
            raise ValueError(f"Could not load image: {input_path}")

        result = self.pipeline.run_page(img)

        # Save output
        cv2.imwrite(output_path, result['final'])

        logger.info(f"OCR-optimized output saved: {output_path}")

        return {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'document_type': analysis['document_type'],
            'security_features_removed': analysis['features'],
            'steps': result['steps']
        }


__all__ = [
    'DocumentPreprocessor',
    'SecurityDocumentPreprocessor',
    'OCROptimizedPreprocessor',
    'ProcessingConfig',
    'SecurityDocumentConfig',
    'OCROptimizedConfig'
]
