# Backend Dockerfile for AutoOCR
# Supports CPU-only and optional GPU acceleration
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for opencv, tesseract, pdf rendering, barcode detection
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    poppler-utils \
    libzbar0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY autoocr ./autoocr
COPY config ./config

# Create non-root user for security
RUN useradd -m -u 1000 autoocr && \
    chown -R autoocr:autoocr /app

USER autoocr

EXPOSE 8000

# Default: Run FastAPI server
CMD ["uvicorn", "autoocr.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# For CLI usage, override with:
# docker run autoocr autoocr preprocess input.pdf output.pdf
