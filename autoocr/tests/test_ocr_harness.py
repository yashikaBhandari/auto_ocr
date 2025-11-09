"""Tests for OCR harness (mocked OCR to avoid external dependency)."""
from __future__ import annotations

import types

import numpy as np

from autoocr.api.utils import ocr_harness
from autoocr.api.pipeline import Pipeline


class DummyTesseractModule:
    def image_to_string(self, image, lang="eng"):
        # Return constant text regardless of image; processed vs baseline identical
        return "SAMPLE TEXT"


def test_run_ocr_harness_monkeypatch(monkeypatch):
    # Monkeypatch pytesseract functions used inside harness
    dummy = DummyTesseractModule()
    monkeypatch.setattr(ocr_harness, "pytesseract", dummy)

    # Build a 1-page fake PDF replacement by directly feeding image bytes
    # Instead, we patch pdf_to_images to bypass poppler usage.
    def fake_pdf_to_images(pdf_bytes: bytes):  # noqa: D401
        img = np.full((100, 200, 3), 255, dtype=np.uint8)
        return [img]

    monkeypatch.setattr(ocr_harness, "pdf_to_images", fake_pdf_to_images)

    report = ocr_harness.run_ocr_harness(b"%PDF FAKE", pipeline=Pipeline())
    assert "aggregates" in report
    assert report["aggregates"]["page_count"] == 1
    page = report["pages"][0]
    assert page["similarity_processed"] == 100.0
    # delta zero because identical texts
    assert page["delta"] == 0.0