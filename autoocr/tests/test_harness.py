"""Basic tests for pipeline structure and module contracts.

We avoid running external OCR (Tesseract) here to keep tests lightweight
and not dependent on system binaries.
"""
import numpy as np

from autoocr.api.pipeline import Pipeline


def synthetic_image(text: str = "AUTO OCR"):
    import cv2
    img = np.full((300, 600, 3), 255, dtype=np.uint8)
    cv2.putText(img, text, (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3, cv2.LINE_AA)
    # Add artificial black border to trigger edge mask
    cv2.rectangle(img, (0, 0), (599, 299), (0, 0, 0), 10)
    return img


def test_pipeline_runs_all_modules():
    pipe = Pipeline()
    img = synthetic_image()
    result = pipe.run_document([img])[0]
    assert "steps" in result and len(result["steps"]) >= 5
    # Ensure each step dict has required keys
    for step in result["steps"]:
        for key in ("module", "detected", "applied", "detect_meta", "process_meta"):
            assert key in step
    # Final image shape remains same
    assert result["final"].shape == img.shape


def test_edge_mask_detection():
    pipe = Pipeline()
    img = synthetic_image()
    result = pipe.run_page(img)
    edge_step = next(s for s in result["steps"] if s["module"] == "edge_mask")
    assert edge_step["detected"] is True
    assert edge_step["applied"] is True
