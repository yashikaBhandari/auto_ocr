"""Pipeline orchestrator.

Contract (initial draft):
- Each module implements: should_run(image) -> (bool, metadata) and run(image, metadata) -> (processed_image, result_metadata)
- Pipeline decides order. We keep modules lightweight and stateless.

We introduce a BaseModule class (see modules/base_module.py) handling common interface.
"""
from typing import List, Dict, Any
import cv2
import time
from .utils.logging import get_logger

logger = get_logger("pipeline")

from .modules.base_module import BaseModule
from .modules.edge_mask import EdgeMaskModule
from .modules.orientation import OrientationModule
from .modules.perspective import PerspectiveModule
from .modules.language import LanguageModule
from .modules.deskew import DeskewModule
from .modules.dots_removal import DotsRemovalModule
from .modules.denoise import DenoiseModule
from .modules.enhance import EnhanceModule
from .modules.text_refine import TextRefineModule
from .modules.binarize import BinarizeModule

class Pipeline:
    def __init__(self, modules: List[BaseModule] | None = None):
        if modules is None:
            modules = [
                EdgeMaskModule(),         # mask black borders
                OrientationModule(),      # rotate to upright
                PerspectiveModule(),      # perspective flatten (if needed)
                LanguageModule(),         # detect language (no image change)
                DeskewModule(),           # straighten slight skew
                DotsRemovalModule(),      # remove background dots/speckles
                DenoiseModule(),          # reduce noise if needed
                EnhanceModule(),          # contrast + sharpen / brightness normalize
                TextRefineModule(),       # speckle cleanup & morphological refine
                BinarizeModule(),         # final adaptive threshold (Sauvola/adaptive)
            ]
        self.modules = modules

    def run_page(self, image) -> Dict[str, Any]:
        """Run detection + conditional processing for a single page image.

        Returns dict with keys:
          original: original image (BGR)
          final: final processed image (BGR)
          steps: list of {module, detected, applied, meta}
        """
        work_img = image.copy()
        steps = []
        pre_binarize_snapshot = None
        for module in self.modules:
            t0 = time.time()
            detected, detect_meta = module.detect(work_img)
            t1 = time.time()
            applied = False
            process_meta = None
            if detected:
                # Capture snapshot before binarization if this is the binarize module
                if module.name == "binarize":
                    pre_binarize_snapshot = work_img.copy()
                work_img, process_meta = module.process(work_img, detect_meta)
                applied = True
            t2 = time.time()
            logger.debug(
                f"module={module.name} detected={detected} applied={applied} detect_ms={(t1-t0)*1000:.2f} process_ms={(t2-t1)*1000:.2f}")
            steps.append({
                "module": module.name,
                "detected": bool(detected),
                "applied": applied,
                "detect_meta": detect_meta,
                "process_meta": process_meta,
                "timing_ms": {
                    "detect": round((t1 - t0) * 1000, 2),
                    "process": round((t2 - t1) * 1000, 2) if applied else 0.0,
                    "total": round((t2 - t0) * 1000, 2),
                }
            })
        return {
            "original": image,
            "final": work_img,
            "pre_binarize": pre_binarize_snapshot,
            "steps": steps,
        }

    def run_document(self, pages: List):
        results = []
        for idx, page in enumerate(pages):
            result = self.run_page(page)
            result["page_index"] = idx
            results.append(result)
        return results

__all__ = ["Pipeline"]
