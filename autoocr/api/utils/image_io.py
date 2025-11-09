"""Robust PDF ↔ image helpers with safety & configurability.

Features added over baseline implementation:
  - DPI control (default 300 for sharper OCR).
  - Graceful error handling (corrupt PDF / missing poppler).
  - Page limiting (`max_pages`) and total pixel budget guard (`max_total_pixels`).
  - Optional grayscale output to reduce memory.
  - Optional metadata collection (dimensions, dpi, index).
  - Memory / size safeguards to prevent OOM on huge PDFs.
  - Configurable PDF export (optimize, JPEG quality, RGB forcing, downscale).

Backwards compatibility:
  Existing calls (`pdf_to_images(bytes)`) still work, returning a list of BGR numpy arrays.
  New parameters are optional with sane defaults.
"""
from __future__ import annotations

from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, asdict
from io import BytesIO
import math
import os

import cv2
import numpy as np
from pdf2image import convert_from_bytes
from PIL import Image

###############################################################################
# Data structures
###############################################################################

@dataclass
class PageMeta:
    index: int
    width: int
    height: int
    dpi: int
    mode: str

###############################################################################
# PDF -> Images
###############################################################################

def pdf_to_images(
    pdf_bytes: bytes,
    dpi: int = 300,
    grayscale: bool = False,
    max_pages: Optional[int] = None,
    max_total_pixels: int = 250_000_000,  # ~250M px ≈ <1 GB @ uint8 * 3
    return_metadata: bool = False,
    poppler_path: Optional[str] = None,
) -> List[np.ndarray] | Tuple[List[np.ndarray], List[PageMeta]]:
    """Convert PDF bytes to list of images (BGR or GRAY) with safeguards.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw PDF content.
    dpi : int, default 300
        Rasterization resolution. 300 is a good OCR balance.
    grayscale : bool, default False
        If True, returns single-channel grayscale arrays (uint8). Otherwise BGR.
    max_pages : Optional[int]
        Hard limit on number of pages processed (truncate beyond this count).
    max_total_pixels : int, default 250_000_000
        Total pixel budget across all pages (width*height summed). Raises if exceeded.
    return_metadata : bool, default False
        If True, returns (images, metadata_list). Else just images list.
    poppler_path : Optional[str]
        Explicit path to poppler binaries (Windows or custom installations).

    Returns
    -------
    images : list[np.ndarray]
        List of BGR or GRAY images.
    metadata : list[PageMeta]
        (Only if return_metadata=True) page dimension + dpi info.

    Raises
    ------
    RuntimeError
        If PDF cannot be rasterized or pixel budget exceeded.
    """
    try:
        kwargs: Dict[str, Any] = {"dpi": dpi}
        if poppler_path:
            kwargs["poppler_path"] = poppler_path
        pil_pages = convert_from_bytes(pdf_bytes, **kwargs)
    except Exception as e:  # pylint: disable=broad-except
        msg = (
            f"PDF rasterization failed: {e}. If this is a poppler issue, "
            "install poppler (macOS: 'brew install poppler', Ubuntu: 'apt-get install poppler-utils')."
        )
        raise RuntimeError(msg) from e

    if max_pages is not None:
        pil_pages = pil_pages[:max_pages]

    images: List[np.ndarray] = []
    meta: List[PageMeta] = []
    total_pixels = 0
    for i, pil_img in enumerate(pil_pages):
        arr_rgb = np.array(pil_img)  # RGB
        h, w = arr_rgb.shape[:2]
        total_pixels += (h * w)
        if total_pixels > max_total_pixels:
            raise RuntimeError(
                f"Aborting: total pixel budget exceeded (> {max_total_pixels}). Consider lowering dpi or limiting pages."  # noqa: E501
            )
        if grayscale:
            gray = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2GRAY)
            images.append(gray)
            mode = "GRAY"
        else:
            bgr = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
            images.append(bgr)
            mode = "BGR"
        meta.append(PageMeta(index=i, width=w, height=h, dpi=dpi, mode=mode))

    return (images, meta) if return_metadata else images

###############################################################################
# Images -> PDF
###############################################################################

def images_to_pdf(
    images: List[np.ndarray],
    optimize: bool = True,
    jpeg_quality: int = 85,
    force_rgb: bool = True,
    downscale_max_dim: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Convert list of images (BGR or GRAY) to a single PDF.

    Parameters
    ----------
    images : list[np.ndarray]
        Input images (BGR 3-channel or single-channel grayscale).
    optimize : bool
        Pass Pillow optimize flag (can reduce size).
    jpeg_quality : int
        Quality hint (applies to JPEG-encoded streams; 1–95 typical).
    force_rgb : bool
        Convert grayscale to RGB for wider PDF viewer compatibility.
    downscale_max_dim : Optional[int]
        If set, downscale any dimension > this threshold maintaining aspect ratio.
    metadata : Optional[Dict[str, Any]]
        Placeholder for future PDF metadata embedding (unused currently).

    Returns
    -------
    bytes
        PDF binary.

    Raises
    ------
    ValueError
        If no images provided or unsupported image shape.
    """
    if not images:
        raise ValueError("No images to write")

    pil_pages: List[Image.Image] = []
    for arr in images:
        if arr.ndim == 2:  # grayscale
            work = arr
            if force_rgb:
                work = cv2.cvtColor(work, cv2.COLOR_GRAY2RGB)
            pil_img = Image.fromarray(work)
        elif arr.ndim == 3 and arr.shape[2] == 3:
            rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
        else:
            raise ValueError(f"Unsupported image shape: {arr.shape}")

        if downscale_max_dim:
            w, h = pil_img.size
            scale = min(downscale_max_dim / max(w, h), 1.0)
            if scale < 1.0:
                new_size = (int(w * scale), int(h * scale))
                pil_img = pil_img.resize(new_size, Image.LANCZOS)
        pil_pages.append(pil_img)

    buf = BytesIO()
    first, *rest = pil_pages
    save_kwargs: Dict[str, Any] = {
        "format": "PDF",
        "save_all": True,
        "append_images": rest,
    }
    if optimize:
        save_kwargs["optimize"] = True
    if 1 <= jpeg_quality <= 95:
        save_kwargs["quality"] = jpeg_quality

    # (Future) embed metadata via first.info / PdfImagePlugin, currently skipped.
    first.save(buf, **save_kwargs)
    return buf.getvalue()

###############################################################################
# Convenience wrappers preserving original API semantics
###############################################################################

def pdf_to_images_simple(pdf_bytes: bytes) -> List[np.ndarray]:  # legacy helper
    """Backward-compatible thin wrapper (BGR list @300 DPI)."""
    return pdf_to_images(pdf_bytes, dpi=300, grayscale=False, return_metadata=False)  # type: ignore


__all__ = [
    "pdf_to_images",
    "pdf_to_images_simple",
    "images_to_pdf",
    "PageMeta",
]
