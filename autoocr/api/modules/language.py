"""Language detection module using fastText + lightweight OCR sampling.

Upgrade summary:
  - Performs a quick (downscaled) OCR on the page to extract a text sample.
  - Uses fastText language identification model (lid.176.bin) to predict language.
  - Returns language code + probability. Does not alter the image.

Performance considerations:
  - Downscales large pages to max width 1600 px before OCR to reduce latency.
  - Truncates OCR text to first 1000 characters for prediction.
  - If OCR yields too little text or model missing, gracefully skips with metadata.

Detection semantics:
  - We report `detected=True` when we successfully infer a language so that
    pipeline consumers can see it explicitly as an applied metadata step.
  - Processing remains a no-op; image is returned unchanged.
"""
from __future__ import annotations
from typing import Tuple, Dict, Any, Optional
import os
import cv2
import pytesseract

from .base_module import BaseModule

try:  # optional dependency load
    import fasttext  # type: ignore
except Exception:  # pylint: disable=broad-except
    fasttext = None  # type: ignore


class LanguageModule(BaseModule):
    name = "language"

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.environ.get("FASTTEXT_MODEL")
        self._model = None

    def _load(self):
        if self._model is None and fasttext and self.model_path and os.path.exists(self.model_path):
            try:
                self._model = fasttext.load_model(self.model_path)
            except Exception:  # pylint: disable=broad-except
                self._model = None

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:  # noqa: D401
        self._load()
        if self._model is None:
            return False, {"reason": "model_unavailable"}
        # Check tesseract availability early; skip gracefully if missing.
        try:
            _ = pytesseract.get_tesseract_version()
        except (pytesseract.pytesseract.TesseractNotFoundError, OSError):
            return False, {"reason": "tesseract_missing"}
        # Downscale for faster OCR if very large
        h, w = image.shape[:2]
        scale = 1.0
        max_w = 1600
        if w > max_w:
            scale = max_w / w
        work = image
        if scale < 1.0:
            work = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        try:
            text = pytesseract.image_to_string(th, config='--psm 6')
        except Exception as e:  # pylint: disable=broad-except
            return False, {"reason": "ocr_failed", "error": str(e)}
        cleaned = ' '.join(text.split())
        if len(cleaned) < 20:
            return False, {"reason": "insufficient_text", "length": len(cleaned)}
        sample = cleaned[:1000]
        try:
            labels, probs = self._model.predict(sample, k=1)
            if not labels:
                return False, {"reason": "no_prediction"}
            label = labels[0]
            lang = label.replace('__label__', '')
            prob = float(probs[0]) if probs else 0.0
            return True, {
                "language": lang,
                "probability": round(prob, 4),
                "text_sample_length": len(sample),
                "model_loaded": True,
            }
        except Exception as e:  # pylint: disable=broad-except
            return False, {"reason": "prediction_failed", "error": str(e)}

    def process(self, image, detect_meta: Dict[str, Any]):
        applied = bool(detect_meta.get("language"))
        return image, {"applied": applied}

__all__ = ["LanguageModule"]