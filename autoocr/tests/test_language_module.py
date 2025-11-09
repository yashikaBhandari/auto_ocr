"""Tests for LanguageModule with mocked fastText + OCR."""
from __future__ import annotations

from autoocr.api.modules.language import LanguageModule


class DummyModel:
    def predict(self, text, k=1):  # noqa: D401
        return ["__label__en"], [0.987654]


def test_language_module_detection(monkeypatch):
    mod = LanguageModule(model_path=None)
    # Inject dummy model directly
    mod._model = DummyModel()  # noqa: SLF001

    # Monkeypatch pytesseract to return sample text
    import autoocr.api.modules.language as lang_mod  # lazy import

    def fake_image_to_string(img, config=None):  # noqa: D401
        return "This is a simple English sample text for language detection."

    monkeypatch.setattr(lang_mod.pytesseract, "image_to_string", fake_image_to_string)

    # Create tiny synthetic image (white canvas)
    import numpy as np
    import cv2
    img = 255 * np.ones((50, 200, 3), dtype=np.uint8)
    cv2.putText(img, "ENGLISH", (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

    detected, meta = mod.detect(img)
    assert detected is True
    assert meta.get("language") == "en"
    assert 0 < meta.get("probability", 0) <= 1