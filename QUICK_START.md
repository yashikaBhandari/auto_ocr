# AutoOCR Quick Start Guide

## Installation

### 1. Basic Setup
```bash
# Clone and enter directory
cd /Users/yashikabhandari/Downloads/myocr

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Install System Dependencies

**macOS:**
```bash
brew install tesseract poppler zbar
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils libzbar0
```

## Usage

### CLI Commands

#### 1. Standard Document Processing
```bash
# Single file
autoocr preprocess input.pdf output.pdf

# With JSON report
autoocr preprocess input.pdf output.pdf --json report.json

# Using custom config
autoocr preprocess input.pdf output.pdf --config config/standard.yaml
```

#### 2. OCR-Optimized Mode (Security Feature Removal)
```bash
# Remove watermarks, guilloche, holograms for better OCR
autoocr preprocess passport.jpg clean.jpg --mode ocr-optimized

# Batch process passports
autoocr batch ./passports ./clean_passports --mode ocr-optimized --json results.json
```

#### 3. Security Mode (Feature Preservation)
```bash
# Preserve all security features
autoocr preprocess id_card.jpg preserved.jpg --mode security
```

#### 4. Batch Processing
```bash
# Process entire directory
autoocr batch ./input_folder ./output_folder

# With specific mode
autoocr batch ./scans ./processed --mode ocr-optimized --config config/ocr_optimized.yaml
```

### Python API

#### Basic Usage
```python
from autoocr.api.preprocessor import DocumentPreprocessor

# Create preprocessor
processor = DocumentPreprocessor()

# Process single file
result = processor.process_file("scan.pdf", "clean.pdf")

# Check results
if result['success']:
    print("Processing complete!")
    print(f"Steps applied: {len(result['steps'])}")
```

#### OCR-Optimized Processing
```python
from autoocr.api.preprocessor import OCROptimizedPreprocessor
from autoocr.api.utils.config import OCROptimizedConfig

# Create custom config
config = OCROptimizedConfig(
    remove_watermarks=True,
    remove_guilloche=True,
    flatten_holograms=True,
    mrz_priority=True,  # Enhance passport MRZ zones
    output_dpi=400,     # Higher DPI for OCR
    gpu=True            # Use GPU if available
)

# Process document
processor = OCROptimizedPreprocessor(config)
result = processor.process_file("passport.jpg", "ocr_ready.jpg")

print(f"Features removed: {result['security_features_removed']}")
print(f"Document type: {result['document_type']}")
```

#### Security Document Processing
```python
from autoocr.api.preprocessor import SecurityDocumentPreprocessor

# Minimal processing that preserves features
processor = SecurityDocumentPreprocessor()
result = processor.process_file("certificate.jpg", "preserved.jpg")

print(f"Features preserved: {result['security_features_preserved']}")
print(f"Compliance: {result['compliance']}")
```

#### Batch Processing
```python
from autoocr.api.preprocessor import DocumentPreprocessor

processor = DocumentPreprocessor()
results = processor.process_batch("./input_folder", "./output_folder")

# Print summary
successful = sum(1 for r in results if r['success'])
print(f"Processed {successful}/{len(results)} files successfully")
```

### FastAPI Server

#### Start Server
```bash
uvicorn autoocr.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### API Requests
```bash
# Process document (returns PDF)
curl -o output.pdf -F file=@input.pdf 'http://localhost:8000/process'

# Get JSON response with metadata
curl -F file=@input.pdf 'http://localhost:8000/process?return_format=json' | jq '.'

# Include page images
curl -F file=@input.pdf 'http://localhost:8000/process?return_format=json&return_pages=true' | jq '.pages_base64_png'

# Filter specific modules
curl -F file=@input.pdf 'http://localhost:8000/process?modules_enabled=edge_mask,deskew&return_format=json'

# Check metrics
curl http://localhost:8000/metrics | jq '.'
```

## Configuration Examples

### Custom YAML Config

Create `my_config.yaml`:
```yaml
pipeline:
  # Core settings
  border_threshold: 50
  deskew_enabled: true
  noise_reduction: true
  speck_size: 10
  contrast_enhancement: true

  # Security feature handling
  remove_watermarks: true
  remove_guilloche: true
  flatten_holograms: false

  # MRZ enhancement (for passports)
  mrz_priority: true
  preserve_mrz: true

  # Output settings
  output_dpi: 400
  output_format: "tiff"

  # Performance
  gpu: auto  # Use GPU if available
```

Use it:
```bash
autoocr preprocess input.pdf output.pdf --config my_config.yaml
```

### Python Configuration

```python
from autoocr.api.utils.config import ProcessingConfig, OCROptimizedConfig
from pathlib import Path

# Load from YAML
config = OCROptimizedConfig.from_yaml(Path("config/ocr_optimized.yaml"))

# Or create programmatically
config = ProcessingConfig(
    deskew_enabled=True,
    noise_reduction=True,
    contrast_enhancement=True,
    preserve_barcodes=True,
    gpu=True,
    output_dpi=300
)

# Use with preprocessor
from autoocr.api.preprocessor import DocumentPreprocessor
processor = DocumentPreprocessor(config)
```

## Docker Usage

### Build Image
```bash
docker build -t autoocr .
```

### Run Server
```bash
docker run -p 8000:8000 autoocr
```

### Run CLI
```bash
# Mount local directory
docker run -v /path/to/documents:/data autoocr \
  autoocr preprocess /data/input.pdf /data/output.pdf

# With mode selection
docker run -v /path/to/documents:/data autoocr \
  autoocr preprocess /data/passport.jpg /data/clean.jpg --mode ocr-optimized

# Batch processing
docker run -v /path/to/documents:/data autoocr \
  autoocr batch /data/input /data/output --mode standard --json /data/report.json
```

### With GPU Support
```bash
# Requires nvidia-docker
docker run --gpus all -v /path/to/documents:/data autoocr \
  autoocr preprocess /data/input.pdf /data/output.pdf --config /data/gpu_config.yaml
```

## Testing

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_security_features.py -v

# With coverage report
pytest tests/ --cov=autoocr --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Ensure you're in virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 2. Missing System Dependencies
```bash
# macOS
brew install tesseract poppler zbar

# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils libzbar0
```

#### 3. GPU Not Detected
```python
# Check GPU availability
from autoocr.api.utils.gpu_manager import get_gpu_manager

gpu = get_gpu_manager()
print(f"CUDA available: {gpu.has_cuda}")

# Force CPU mode
gpu = get_gpu_manager(force_cpu=True)
```

#### 4. Deskew Module Errors
```bash
# Install deskew library
pip install deskew

# Or use without deskew
autoocr preprocess input.pdf output.pdf --modules-enabled edge_mask,enhance,binarize
```

## Processing Modes Comparison

| Feature | Standard | Security | OCR-Optimized |
|---------|----------|----------|---------------|
| Edge Masking | ✅ | ✅ | ✅ |
| Deskew | ✅ | ✅ (>2°) | ✅ |
| Denoise | ✅ | ✅ (minimal) | ✅ (aggressive) |
| Contrast Enhancement | ✅ | ❌ | ✅ |
| Guilloche Removal | ❌ | ❌ | ✅ |
| Watermark Removal | ❌ | ❌ | ✅ |
| Hologram Removal | ❌ | ❌ | ✅ |
| MRZ Enhancement | ❌ | ❌ | ✅ |
| Binarization | ✅ | ❌ | ✅ |
| Preserve Security | N/A | ✅ | ❌ |

## Performance Tips

### 1. Enable GPU Acceleration
```python
config = ProcessingConfig(gpu=True)
# 2.7x speedup on NVIDIA GPUs
```

### 2. Batch Processing
```bash
# More efficient than individual files
autoocr batch ./input ./output
```

### 3. Optimize Output Format
```python
# TIFF for quality, PDF for distribution
config = ProcessingConfig(output_format="tiff", output_dpi=300)
```

### 4. Selective Module Execution
```bash
# Only run needed modules
curl -F file=@input.pdf 'http://localhost:8000/process?modules_enabled=edge_mask,deskew'
```

## Next Steps

1. **Try Examples**: Process sample documents in each mode
2. **Customize Config**: Create YAML configs for your use cases
3. **Batch Process**: Set up automated workflows
4. **Monitor Performance**: Use `/metrics` endpoint
5. **Integrate OCR**: Pipe output to Tesseract/OCRmyPDF

## Getting Help

- **Documentation**: See `README.md` and `IMPLEMENTATION_SUMMARY.md`
- **Examples**: Check `config/` directory for YAML templates
- **Tests**: Review `tests/test_security_features.py` for usage patterns
- **API Docs**: Visit `http://localhost:8000/docs` when server is running

## Legal Notice

⚠️ **Security Document Processing Warning**

When using OCR-Optimized mode on security documents:
- Ensure you have legal authorization
- Maintain audit trails
- Follow local regulations
- Use only for legitimate purposes

This tool is designed for:
- ✅ Authorized document processing
- ✅ OCR accuracy improvement
- ✅ Digital archival
- ❌ Document forgery or fraud
