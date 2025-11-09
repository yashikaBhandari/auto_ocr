"""FastAPI entrypoint for AutoOCR backend.

Flow (high-level now, implementation will grow):
1. Accept PDF upload (multipart) or single image.
2. Convert PDF pages to images (utils.pdf_io) – deferred until utility implemented.
3. Run pipeline on each page (pipeline.run_document).
4. Return processed PDF (as downloadable) + optional per-page diagnostics.

For now we expose:
- GET /health -> simple readiness probe.
- POST /process -> placeholder returning NOT_IMPLEMENTED until pipeline ready.

We keep code minimal initially so we can layer modules incrementally.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import base64
import io
import cv2
import numpy as np
from typing import List

from .pipeline import Pipeline
from .utils.image_io import pdf_to_images, images_to_pdf
from .utils.metrics import metrics
from .utils.logging import get_logger

logger = get_logger("api")

pipeline = Pipeline()

app = FastAPI(title="AutoOCR Preprocessing API", version="0.1.0")

# CORS (allow all for development; tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount built frontend if present (Vite build output under frontend/react-app/dist)
import os  # noqa: E402
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "react-app", "dist")
if os.path.isdir(frontend_dist):  # pragma: no cover
    # Mount under /frontend to avoid shadowing API routes like /health and /process.
    # Access UI at /frontend/ (FastAPI StaticFiles provides index.html automatically).
    app.mount("/frontend", StaticFiles(directory=frontend_dist, html=True), name="frontend")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
    return_pdf: bool = True,
    return_pages: bool = False,
    return_color: bool = False,
    modules_enabled: str | None = None,
    return_format: str = Query("pdf", pattern="^(pdf|json|both)$", description="Response format: pdf|json|both"),
):
    """Process an uploaded PDF or image and return preprocessing metadata.

    Query params:
      return_pdf: include processed PDF as binary stream
      return_pages: include list of base64 encoded final page images (PNG)
    """
    filename = file.filename.lower()
    data = await file.read()
    if not filename.endswith((".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Load pages
    if filename.endswith(".pdf"):
        try:
            pages = pdf_to_images(data)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"pdf_conversion_failed error={e}")
            raise HTTPException(status_code=500, detail=f"PDF conversion failed: {e}") from e
    else:
        # Single image
        np_arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Image decode failed")
        pages = [img]

    # Dynamic module filtering if modules_enabled provided
    if modules_enabled:
        enabled_set = {m.strip() for m in modules_enabled.split(',') if m.strip()}
        original_modules = pipeline.modules
        filtered: List = [m for m in original_modules if m.name in enabled_set]
        if not filtered:
            raise HTTPException(status_code=400, detail="No valid modules after filtering")
        pipeline.modules = filtered
        results = pipeline.run_document(pages)
        pipeline.modules = original_modules  # restore
    else:
        results = pipeline.run_document(pages)
    processed_images = [r["final"] for r in results]
    pre_binarize_images = [r.get("pre_binarize") for r in results]

    response_payload = {
        "filename": file.filename,
        "page_count": len(pages),
        "steps": [
            {
                "page_index": r["page_index"],
                "modules": r["steps"],
            } for r in results
        ]
    }

    if return_pages:
        encoded_pages = []
        for idx, img in enumerate(processed_images):
            success, buf = cv2.imencode('.png', img)
            if success:
                encoded_pages.append(base64.b64encode(buf.tobytes()).decode('utf-8'))
            else:
                encoded_pages.append(None)
        response_payload["pages_base64_png"] = encoded_pages

    if return_color and pre_binarize_images and any(pre_binarize_images):
        color_pages = []
        for img in pre_binarize_images:
            if img is None:
                color_pages.append(None)
                continue
            success, buf = cv2.imencode('.png', img)
            if success:
                color_pages.append(base64.b64encode(buf.tobytes()).decode('utf-8'))
            else:
                color_pages.append(None)
        response_payload["pages_color_before_binarize_png"] = color_pages

    applied_count = sum(sum(1 for s in r["steps"] if s["applied"]) for r in results)
    metrics.inc_request(len(pages), applied_count)
    logger.info(f"processed filename={file.filename} pages={len(pages)} modules_applied={applied_count}")

    # Always generate PDF bytes if caller wants a PDF (even for json/both so we can embed)
    if return_pdf:
        try:
            # Choose which set of images for main PDF: if return_color requested, prefer color (pre-binarize) when available
            pdf_source_images = processed_images
            if return_color and any(pre_binarize_images):
                # Use color snapshots where available, else fallback to processed
                pdf_source_images = [c if c is not None else p for c, p in zip(pre_binarize_images, processed_images)]
            pdf_bytes = images_to_pdf(pdf_source_images)
            if return_format == "pdf" and not return_pages and not return_color:
                return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={
                    'X-AutoOCR-Meta': base64.b64encode(JSONResponse(content=response_payload).body).decode('utf-8'),
                    'Content-Disposition': f'attachment; filename="processed_{file.filename.rsplit('/',1)[-1]}"'
                })
            # Embed base64 PDF for json/both variants
            response_payload['pdf_base64'] = base64.b64encode(pdf_bytes).decode('utf-8')
            if return_color and any(pre_binarize_images):
                # Also embed binary version if color chosen so user can compare
                binary_pdf_bytes = images_to_pdf(processed_images)
                response_payload['binary_pdf_base64'] = base64.b64encode(binary_pdf_bytes).decode('utf-8')
        except Exception as e:  # pylint: disable=broad-except
            response_payload['pdf_error'] = str(e)
            return JSONResponse(response_payload)

    return JSONResponse(response_payload)


@app.get("/metrics")
async def metrics_endpoint():
    return metrics.snapshot()
