"""Tests for enhanced image_io utilities (non-poppler dependent parts)."""
from __future__ import annotations

import numpy as np

from autoocr.api.utils.image_io import images_to_pdf


def test_images_to_pdf_basic():
    # Create 2 synthetic BGR images
    img1 = np.zeros((100, 150, 3), dtype=np.uint8)
    img1[:] = (255, 255, 255)
    img2 = np.zeros((80, 120, 3), dtype=np.uint8)
    pdf_bytes = images_to_pdf([img1, img2])
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 100
