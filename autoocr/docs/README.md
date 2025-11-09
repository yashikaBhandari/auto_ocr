# AutoOCR Docs (Work in Progress)

## Architecture Overview
Components:
1. FastAPI backend (`autoocr/api`) orchestrating preprocessing modules.
2. Modular detection+processing pipeline (each module self-contained).
3. React demo frontend (upload, preview before/after planned).
4. Test harness to quantify OCR improvement.

## Pipeline Philosophy
Detect first, process only when needed:
- Edge masking avoids destructive crops.
- Orientation & deskew stabilize geometry.
- Denoise improves text clarity.
- Enhancement + binarization optimize for OCR engine.

## Next Steps
Populate docs with sequence diagrams, threshold tuning guide, and benchmarking method.

## Module Catalog
| Module | Type | Detection Strategy | Processing Action |
|--------|------|--------------------|-------------------|
| edge_mask | structural | Largest contour area ratio < threshold | Mask border white (non-destructive) |
| orientation | geometric | Tesseract OSD angle in {90,180,270} | Rotate to upright |
| language | metadata | (Placeholder) requires fastText model | No-op (metadata only) |
| deskew | geometric | minAreaRect angle | Affine rotate |
| denoise | quality | Laplacian variance below threshold | fastNlMeans / median fallback |
| enhance | quality | Low grayscale std dev | CLAHE + unsharp mask |
| binarize | finalization | Always true (configurable) | Adaptive Gaussian threshold |

## API Flow (/process)
1. Accept upload (PDF or image)
2. Convert PDF pages to BGR images
3. Run pipeline sequentially per page
4. Collect step metadata (audit trail)
5. Return PDF stream (processed) and/or base64 images & JSON metadata

### Sample Metadata (trimmed)
```json
{
	"page_index": 0,
	"modules": [
		{"module": "edge_mask", "detected": true, "applied": true, "detect_meta": {"area_ratio": 0.83}},
		{"module": "orientation", "detected": false, "applied": false},
		{"module": "language", "detected": false, "applied": false, "detect_meta": {"reason": "model_unavailable"}}
	]
}
```

## Test Harness (Planned OCR Comparison)
Will produce JSON report with fields:
- per_page: original_text, processed_text, similarity_score
- aggregates: average_similarity, improvement_delta

Similarity computed with RapidFuzz (e.g., fuzz.QRatio or token_set_ratio). Improvements >5–10% often indicate beneficial preprocessing; near-zero suggests over-processing or already clean input.

## Threshold Tuning Guidelines
- Edge area ratio: start 0.90; raise if false positives (inside margins) appear.
- Laplacian variance: compute distribution across dataset; choose e.g. 25th percentile.
- Contrast std: log values for clean vs faint scans; pick midpoint.

## Language Detection Notes
Current module is a placeholder (no-op) until integrating fastText model. After model download:
```bash
curl -O https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
export FASTTEXT_MODEL=$PWD/lid.176.bin
```
Then detection metadata will include candidate language codes.
