"""Centralized configuration & thresholds.
Adjust values here to tune sensitivity without editing module logic.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import yaml

EDGE_AREA_THRESHOLD = 0.90  # ratio; if largest contour smaller -> border assumed
LAPLACIAN_VARIANCE_NOISE_THRESHOLD = 50.0
LOW_CONTRAST_STD_THRESHOLD = 40.0
SKEW_DEGREE_MIN = 0.5  # absolute degrees above which we deskew

# Additional quality thresholds
LAPLACIAN_VARIANCE_SHARPNESS_THRESHOLD = 120.0  # below -> potentially blurry, trigger enhancement
BRIGHTNESS_LOW_THRESHOLD = 80.0
BRIGHTNESS_HIGH_THRESHOLD = 220.0
NOISE_LEVEL_THRESHOLD = 12.0  # mean absolute diff vs Gaussian blur; above -> denoise
OCR_CONFIDENCE_MIN = 60.0  # (future use) below -> force aggressive enhancement

# Text refinement / speckle cleanup
SPECKLE_COMPONENT_MAX_AREA = 30  # tiny blobs threshold
SPECKLE_RATIO_THRESHOLD = 0.35  # fraction of tiny blobs among all components

# Sauvola adaptive threshold parameters
SAUVOLA_WINDOW_SIZE = 25
SAUVOLA_K = 0.2

# Unsharp mask parameters
UNSHARP_AMOUNT = 1.5
UNSHARP_GAUSSIAN_KERNEL = (5, 5)
UNSHARP_SIGMA = 0

# CLAHE parameters
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)


@dataclass
class ProcessingConfig:
    """Configuration dataclass with type safety for production-grade preprocessing"""
    # Core corrections
    border_threshold: int = 50
    deskew_enabled: bool = True
    noise_reduction: bool = True
    speck_size: int = 10
    contrast_enhancement: bool = True

    # Advanced AI features
    ai_warp_correction: bool = False
    finger_removal: bool = False

    # Preservation settings
    preserve_barcodes: bool = True
    preserve_qrcodes: bool = True
    preserve_signatures: bool = False

    # Output settings
    output_dpi: int = 300
    output_format: str = "pdfa"  # pdfa, tiff, png
    preserve_metadata: bool = True

    # Masking vs cropping
    masking_enabled: bool = True
    mask_output_path: Optional[str] = None

    # GPU settings
    gpu: bool = False

    @classmethod
    def from_yaml(cls, path: Path):
        """Load configuration from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data.get('pipeline', {}))


@dataclass
class SecurityDocumentConfig(ProcessingConfig):
    """Specialized config for security documents (preserves security features)"""
    document_type: str = "auto"  # passport, id_card, certificate, currency, auto
    security_mode: bool = True
    preserve_background: bool = True
    preserve_color: bool = True
    max_denoising: int = 3
    allow_binarization: bool = False
    allow_contrast_boost: bool = False
    watermark_threshold: float = 0.95


@dataclass
class OCROptimizedConfig(ProcessingConfig):
    """Config for aggressive security feature removal to maximize OCR accuracy"""
    # Security feature removal (opposite of SecurityDocumentConfig)
    remove_watermarks: bool = True
    remove_guilloche: bool = True
    flatten_holograms: bool = True
    mrz_priority: bool = True
    text_enhancement: str = "aggressive"
    security_feature_threshold: float = 0.85

    # Legal compliance
    legal_compliance_check: bool = True

    # Always preserve MRZ even when removing other features
    preserve_mrz: bool = True

    # Override parent defaults for OCR optimization
    allow_binarization: bool = True
    allow_contrast_boost: bool = True
    preserve_color: bool = False
