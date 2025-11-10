# AutoOCR Preprocessing Pipeline

An automated, modular preprocessing system for scanned / photographed documents to maximize downstream OCR accuracy.

## Key Features
- Adaptive always-on cleaning: Denoise & Enhance now always run with dynamic strength (never miss subtle noise), reporting metrics.
- Non-destructive edge masking (vs risky cropping).
- Orientation + deskew stabilization.
- Quality refinement (text_refine) with speckle cleanup and safe rollback.
- Dual-stage adaptive binarization (Sauvola fallback to Gaussian) for crisp glyph edges.
- Full audit trail: per-module metrics (contrast, noise_level, laplacian_variance, timings).
- Test harness to quantify improvement (text similarity pre vs post).

## Repository Layout
```
autoocr/
  api/
    main.py          # FastAPI entrypoint
    pipeline.py      # Orchestrator
    modules/         # Individual preprocessing modules
    utils/           # IO & config helpers
  tests/
    test_harness.py  # Placeholder (will evolve)
  docs/              # Architecture & design docs
  frontend/
    react-app/       # Demo UI placeholder
```

## Backend Quick Start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn autoocr.api.main:app --reload
```

Process a file (receive PDF stream):
```bash
curl -o out.pdf -F file=@sample.pdf 'http://localhost:8000/process'
```

Request JSON + embedded PDF & page PNGs:
```bash
curl -s -F file=@sample.pdf 'http://localhost:8000/process?return_format=json&return_pages=true' | jq '.'
```

Filter modules:
```bash
curl -s -F file=@sample.pdf 'http://localhost:8000/process?modules_enabled=edge_mask,deskew&return_format=json' | jq '.steps[0].modules[] | {module,detected,applied}'
```

`X-AutoOCR-Meta` response header (when `return_format=pdf`) contains base64 JSON metadata.

## Philosophy
Originally "detect, then act"; evolved to "measure, adapt, always protect text". Enhancement & denoise are applied every time, but intensity scales with measured contrast/noise to avoid over sharpening or blurring.

## Roadmap
- [x] Initial scaffold
- [x] Dependency pinning
- [x] All core preprocessing modules (edge_mask, orientation, perspective, language, deskew, denoise, enhance, binarize)
- [x] PDF IO (images->PDF, PDF->images) with pixel budget guard
- [x] FastAPI /process endpoint (pdf|json|both variants)
- [x] Test harness & similarity metrics
- [x] Dockerization
- [x] JSON logging & metrics endpoint
- [x] Frontend scaffold (React + Vite)
- [ ] Frontend build & styling polish
- [ ] Multi-language tesseract packs auto-detect
- [ ] Prometheus metrics / OpenTelemetry
- [x] Adaptive always-on denoise/enhance
- [x] Text refinement rollback safeguards
- [ ] OCR confidence feedback loop (auto re-tune if low)
- [ ] Advanced module thresholds tuning

## Frontend (React + Vite)
Located in `autoocr/frontend/react-app`.

### Development
```bash
cd autoocr/frontend/react-app
npm install
npm run dev
```
Set API base (if backend on another origin): create `.env` with:
```
VITE_API_BASE=http://localhost:8000
```

### Build & Serve via FastAPI
```bash
npm run build
cd ../../../..  # project root
uvicorn autoocr.api.main:app --reload
```
The backend auto-mounts the built `dist/` at `/` if present.

### UI Features
- File upload (PDF or image)
- Optional module filtering (`modules_enabled`)
- Per-page PNG preview (when `return_pages=true`)
- Module decision table (detected/applied + timing)
- Embedded processed PDF (download + inline viewer)

## JSON Response Shape (return_format=json)
```jsonc
{
  "filename": "sample.pdf",
  "page_count": 2,
  "steps": [
    {
      "page_index": 0,
      "modules": [
        {
          "module": "edge_mask",
          "detected": true,
          "applied": true,
          "detect_meta": {"area_ratio": 0.83, ...},
          "process_meta": {"border_pixels_masked": 5321},
          "timing_ms": {"detect": 1.7, "process": 0.9, "total": 2.6}
        }
            {
              "module": "denoise",
              "detected": true,
              "applied": true,
              "detect_meta": {"noise_level": 11.2, "laplacian_variance": 145.4, "high_noise": false},
              "process_meta": {"method": "fastNlMeans", "strength": 5},
              "timing_ms": {"detect": 2.1, "process": 12.4, "total": 14.5}
            },
            {
              "module": "enhance",
              "detected": true,
              "applied": true,
              "detect_meta": {"contrast_std": 52.3, "brightness_mean": 138.0},
              "process_meta": {"adaptive_clip_limit": 2.0, "adaptive_unsharp_amount": 1.5, "post_contrast": 68.9},
              "timing_ms": {"detect": 1.5, "process": 8.6, "total": 10.1}
            },
            {
              "module": "text_refine",
              "detected": true,
              "applied": true,
              "detect_meta": {"speckle_ratio": 0.41, "small_components": 128},
              "process_meta": {"components_removed": 91, "reverted_cleanup": false, "white_pixel_ratio": 0.63},
              "timing_ms": {"detect": 3.9, "process": 15.2, "total": 19.1}
            }
      ]
    }
  ],
  "pdf_base64": "JVBERi0xLjc...",
  "pages_base64_png": ["iVBORw0KGgo..."]
}
```

## Metrics Endpoint
```bash
curl -s http://localhost:8000/metrics | jq
```
Returns counts of requests, pages processed, modules applied.

## OCR Harness Usage
```bash
python -m autoocr.api.utils.ocr_harness --input sample.pdf --lang eng --output report.json
```
Generates similarity metrics (RapidFuzz QRatio) between raw & processed OCR text.

## License
Apache 2.0 (proposed) — confirm before release.
