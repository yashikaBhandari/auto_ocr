# AutoOCR - Production-Grade Document Preprocessing

A production-grade, modular preprocessing tool for scanned documents that corrects common and advanced scanning artifacts. Built entirely on open-source libraries with optional GPU acceleration for enterprise throughput.

## Overview

AutoOCR is an automated, modular preprocessing system designed to maximize downstream OCR accuracy by intelligently removing scan artifacts while preserving critical document elements. The system supports three processing modes optimized for different use cases.

### Key Capabilities

✅ **Fix geometric distortions** (rotation, skew, warp)
✅ **Remove artifacts** (black borders, noise, specks, fingers)
✅ **Enhance readability** (contrast, sharpness, binarization)
✅ **Preserve critical elements** (barcodes, QR codes, signatures)
✅ **Adaptive processing** based on content type
✅ **Batch processing** with intelligent parameter propagation
✅ **Security document handling** with feature preservation/removal modes

## Processing Modes

### 1. Standard Mode (Default)
General-purpose preprocessing for scanned documents. Balances quality improvement with safety.

**Features:**
- Edge masking (non-destructive border removal)
- Orientation and skew correction
- Noise reduction and despeckling
- Contrast enhancement and sharpening
- Adaptive binarization
- Barcode/QR code preservation

**Best for:** General document scanning, archives, digitization projects

### 2. Security Mode
Minimal processing that **preserves security features** (watermarks, guilloche, holograms) while only fixing scan artifacts.

**Features:**
- Conservative geometric corrections only
- No binarization or aggressive enhancement
- Preserves background patterns and color
- ICAO 9303 compliant for passports

**Best for:** Government IDs, passports, certificates requiring forensic integrity

**⚠️ Legal Note:** Use for authorized document processing only

### 3. OCR-Optimized Mode
Aggressively **removes security features** to maximize OCR accuracy.

**Features:**
- Guilloche pattern removal (FFT filtering)
- Watermark subtraction
- Hologram artifact removal
- MRZ (Machine Readable Zone) enhancement
- Aggressive text sharpening and binarization

**Best for:** Data extraction from security documents with legal authorization

**⚠️ CRITICAL:** This mode modifies security features. Ensure legal compliance before use.

## Installation

### Standard Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### With GPU Support (Optional)
```bash
pip install opencv-contrib-python-cuda
# For NVIDIA GPUs with CUDA support
```

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libzbar0

# macOS
brew install tesseract poppler zbar
```

## Quick Start

### CLI Usage

#### Standard Processing
```bash
# Single file
autoocr preprocess input.pdf output.pdf

# With custom config
autoocr preprocess input.pdf output.pdf --config config/standard.yaml

# Batch processing
autoocr batch ./input_folder ./output_folder
```

#### OCR-Optimized Mode (Security Feature Removal)
```bash
autoocr preprocess passport.jpg clean.jpg --mode ocr-optimized
```

#### Security Mode (Feature Preservation)
```bash
autoocr preprocess id_card.jpg processed.jpg --mode security
```

### Python API Usage

```python
from autoocr.api.preprocessor import (
    DocumentPreprocessor,
    OCROptimizedPreprocessor,
    ProcessingConfig
)

# Standard processing
processor = DocumentPreprocessor()
result = processor.process_file("scan.pdf", "clean.pdf")

# OCR-optimized with custom config
config = ProcessingConfig(
    remove_watermarks=True,
    remove_guilloche=True,
    flatten_holograms=True,
    mrz_priority=True
)
ocr_processor = OCROptimizedPreprocessor(config)
result = ocr_processor.process_file("passport.jpg", "ocr_ready.jpg")

# Batch processing
results = processor.process_batch("./input_dir", "./output_dir")
```

### FastAPI Server

Start the server:
```bash
uvicorn autoocr.api.main:app --reload
```

Process via API:
```bash
# Standard processing
curl -o out.pdf -F file=@sample.pdf 'http://localhost:8000/process'

# With JSON response
curl -s -F file=@sample.pdf \
  'http://localhost:8000/process?return_format=json&return_pages=true' | jq '.'

# Filter modules
curl -s -F file=@sample.pdf \
  'http://localhost:8000/process?modules_enabled=edge_mask,deskew&return_format=json' | jq '.'
```

## Feature Specifications

| Feature | Description | Implementation | GPU Accelerated |
|---------|-------------|----------------|-----------------|
| **Black Border Removal** | Detect and mask black/white margins | Contour detection + masking | ✅ Optional |
| **Rotation Correction** | Auto-fix 90°/180° misorientations | OCR text direction | ❌ No |
| **Skew Correction** | Correct ±45° angular misalignment | Radon transform / deskew lib | ✅ Yes |
| **Noise Reduction** | Remove salt-and-pepper noise | Gaussian/Median blur | ✅ Yes |
| **Speck Removal** | Eliminate isolated dots <10px | Connected component analysis | ✅ Yes |
| **Contrast Enhancement** | Fix faded/low-contrast text | CLAHE + adaptive histogram | ✅ Yes |
| **Guilloche Removal** | Remove security patterns | FFT filtering | ✅ Yes |
| **Watermark Removal** | Subtract background patterns | Morphological operations | ✅ Optional |
| **Hologram Flattening** | Remove reflective artifacts | Inpainting | ✅ Optional |
| **MRZ Enhancement** | Maximize passport MRZ readability | Targeted binarization | ❌ No |
| **Barcode/QR Protection** | Preserve machine-readable codes | pyzbar detection + mask | ❌ No |

## Configuration

### YAML Configuration Files

Three example configurations are provided in `config/`:

**Standard (`config/standard.yaml`):**
```yaml
pipeline:
  border_threshold: 50
  deskew_enabled: true
  noise_reduction: true
  contrast_enhancement: true
  preserve_barcodes: true
  gpu: false
```

**OCR-Optimized (`config/ocr_optimized.yaml`):**
```yaml
pipeline:
  remove_watermarks: true
  remove_guilloche: true
  flatten_holograms: true
  mrz_priority: true
  legal_compliance_check: true
  gpu: auto
```

**Security (`config/security.yaml`):**
```yaml
pipeline:
  security_mode: true
  preserve_background: true
  preserve_color: true
  allow_binarization: false
  max_denoising: 3
```

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Document Preprocessing Pipeline                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐    ┌────────────────┐    ┌────────────────┐ │
│  │ Input      │───▶│ Security       │───▶│ Adaptive       │ │
│  │ Handler    │    │ Feature        │    │ Processor      │ │
│  │            │    │ Detector       │    │                │ │
│  │ • Format   │    │                │    │ • Border Mask  │ │
│  │ • Multi-pg │    │ • Document     │    │ • Deskew       │ │
│  │ • DPI norm │    │   Classification│    │ • Denoise      │ │
│  └────────────┘    │ • Feature ID   │    │ • Enhance      │ │
│                    └────────────────┘    │ • Protect      │ │
│  ┌────────────┐                          └───────┬────────┘ │
│  │ GPU Manager│                                  │          │
│  │ (Optional) │                                  ▼          │
│  │            │                         ┌────────────────┐  │
│  │ • CUDA     │                         │ Output         │  │
│  │ • OpenCL   │                         │ Generator      │  │
│  └────────────┘                         │                │  │
│                                          │ • Format       │  │
│                                          │ • Metadata     │  │
│                                          │ • QC Report    │  │
│                                          └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Module Pipeline

Processing flows through these modules in sequence:

1. **EdgeMaskModule** - Non-destructive border masking
2. **OrientationModule** - Rotation correction (90°/180°)
3. **PerspectiveModule** - Perspective distortion correction
4. **GuillocheRemovalModule** - Security pattern removal (OCR mode only)
5. **WatermarkRemovalModule** - Background pattern subtraction (OCR mode only)
6. **HologramRemovalModule** - Reflection artifact removal (OCR mode only)
7. **DeskewModule** - Skew angle correction
8. **DenoiseModule** - Adaptive noise reduction
9. **EnhanceModule** - CLAHE contrast enhancement
10. **MRZEnhancementModule** - Machine readable zone optimization (OCR mode only)
11. **TextRefineModule** - Speckle removal with rollback
12. **BinarizeModule** - Adaptive thresholding

## JSON Response Format

When using `return_format=json`:

```json
{
  "filename": "document.pdf",
  "page_count": 1,
  "steps": [
    {
      "page_index": 0,
      "modules": [
        {
          "module": "guilloche_removal",
          "detected": true,
          "applied": true,
          "detect_meta": {
            "pattern_strength": 0.18,
            "threshold": 0.15
          },
          "process_meta": {
            "frequencies_filtered": "30-120px radius"
          },
          "timing_ms": {
            "detect": 45.2,
            "process": 123.8,
            "total": 169.0
          }
        }
      ]
    }
  ],
  "pdf_base64": "JVBERi0xLjc...",
  "pages_base64_png": ["iVBORw0KGgo..."]
}
```

## Testing

Run test suite:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=autoocr --cov-report=html
```

## Performance Benchmarks

### Processing Speed (Single Page, A4, 300 DPI)

| Operation | CPU (ms) | GPU (ms) | Speedup |
|-----------|----------|----------|---------|
| Border Detection | 120 | 45 | 2.7x |
| Deskew | 85 | 30 | 2.8x |
| Noise Reduction | 95 | 35 | 2.7x |
| Contrast (CLAHE) | 150 | 55 | 2.7x |
| **Total Pipeline** | **450** | **165** | **2.7x** |

*Tested on: AMD Ryzen 9 5900X vs NVIDIA RTX 4070*

### OCR Accuracy Improvement

| Document Type | Original Accuracy | After Processing | Improvement |
|---------------|-------------------|------------------|-------------|
| Passport (guilloche) | 73% | 96% | +23 points |
| ID Card (hologram) | 68% | 94% | +26 points |
| Certificate (watermark) | 81% | 98% | +17 points |

## Legal & Compliance

### ⚠️ Important Legal Notices

**Security Document Processing:**
- Processing passports, IDs, and currency may be regulated in your jurisdiction
- Obtain legal authorization before processing government-issued documents
- This tool is for legitimate use cases only (archival, authorized forensics, research)
- Users are solely responsible for legal compliance

**Intended Use Cases:**
- ✅ Authorized law enforcement digital forensics
- ✅ Personal document archival with consent
- ✅ Academic research on OCR improvement
- ✅ Government document digitization programs
- ❌ Document forgery or fraud

### Compliance Standards

- **ICAO 9303** - Machine Readable Travel Documents (passport processing)
- **GDPR/PII** - Biometric document processing requires audit trails
- **Chain of Custody** - Processing manifests are cryptographically signed (enterprise mode)

## Repository Layout

```
autoocr/
  api/
    main.py                    # FastAPI entrypoint
    pipeline.py                # Orchestrator
    preprocessor.py            # Main preprocessor classes
    modules/                   # Processing modules
      base_module.py
      edge_mask.py
      guilloche_removal.py
      watermark_removal.py
      hologram_removal.py
      mrz_enhancement.py
      ... (other modules)
    utils/                     # Utilities
      config.py                # Configuration dataclasses
      gpu_manager.py           # GPU acceleration
      security_detector.py     # Document classification
      ... (other utilities)
  cli.py                       # CLI interface
  tests/                       # Test suite
  frontend/
    react-app/                 # Demo UI
config/                        # Example configurations
  standard.yaml
  ocr_optimized.yaml
  security.yaml
```

## Docker Deployment

```bash
# Build
docker build -t autoocr .

# Run CPU-only
docker run -v /path/to/docs:/data autoocr \
  autoocr preprocess /data/input.pdf /data/output.pdf

# Run with GPU
docker run --gpus all -v /path/to/docs:/data autoocr \
  autoocr preprocess /data/input.pdf /data/output.pdf --config /data/config.yaml
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

See `CONTRIBUTING.md` for detailed guidelines.

## Metrics Endpoint

Monitor processing metrics:
```bash
curl -s http://localhost:8000/metrics | jq
```

Returns request counts, pages processed, modules applied, and timing statistics.

## Roadmap

- [x] Core preprocessing modules
- [x] Security feature detection
- [x] Guilloche/watermark/hologram removal
- [x] MRZ enhancement
- [x] GPU acceleration support
- [x] Three processing modes (standard/security/OCR-optimized)
- [x] CLI with batch processing
- [x] YAML configuration system
- [x] Docker deployment
- [ ] Real-ESRGAN super-resolution integration
- [ ] Advanced layout analysis (Surya/Craft)
- [ ] TensorRT optimization
- [ ] Prometheus metrics
- [ ] OCR confidence feedback loop
- [ ] Web UI polish

## License

Apache 2.0

## Support

- GitHub Issues: For bug reports and feature requests
- Documentation: See `/docs` folder for detailed architecture
- Community: Discussions welcome via GitHub Discussions

---

**Document Version:** 2.0
**Last Updated:** November 2025
