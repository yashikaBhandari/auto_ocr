"""CLI entry points for AutoOCR.

Commands:
  autoocr process <input_path> [--out OUTPUT] [--lang ENG] [--json REPORT_JSON]
  autoocr preprocess <input> <output> [--mode MODE] [--config CONFIG]
  autoocr batch <input_dir> <output_dir> [--mode MODE] [--config CONFIG]
  autoocr harness  <input_path> [--lang ENG] [--json REPORT_JSON]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoocr.api.utils.image_io import pdf_to_images_simple, images_to_pdf
from autoocr.api.pipeline import Pipeline
from autoocr.api.utils.ocr_harness import run_ocr_harness
from autoocr.api.preprocessor import (
    DocumentPreprocessor,
    SecurityDocumentPreprocessor,
    OCROptimizedPreprocessor,
    ProcessingConfig,
    SecurityDocumentConfig,
    OCROptimizedConfig
)


def cmd_process(args):
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")
    pdf_bytes = input_path.read_bytes()
    images = pdf_to_images_simple(pdf_bytes)
    pipe = Pipeline()
    results = pipe.run_document(images)
    processed = [r["final"] for r in results]
    pdf_out = images_to_pdf(processed)
    out_path = Path(args.out or f"processed_{input_path.name}")
    out_path.write_bytes(pdf_out)
    if args.json:
        summary = {
            "input": str(input_path),
            "output": str(out_path),
            "pages": len(results),
            "steps": [
                {"page_index": r["page_index"], "modules": r["steps"]} for r in results
            ],
        }
        Path(args.json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Processed PDF written to {out_path}")


def cmd_preprocess(args):
    """New unified preprocessing command with multiple modes."""
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    # Load config if provided
    config = None
    if args.config:
        config_path = Path(args.config)
        if args.mode == 'security':
            config = SecurityDocumentConfig.from_yaml(config_path)
        elif args.mode == 'ocr-optimized':
            config = OCROptimizedConfig.from_yaml(config_path)
        else:
            config = ProcessingConfig.from_yaml(config_path)

    # Select preprocessor based on mode
    if args.mode == 'standard':
        preprocessor = DocumentPreprocessor(config)
    elif args.mode == 'security':
        preprocessor = SecurityDocumentPreprocessor(config)
    elif args.mode == 'ocr-optimized':
        preprocessor = OCROptimizedPreprocessor(config)
    else:
        raise SystemExit(f"Invalid mode: {args.mode}")

    # Process file
    result = preprocessor.process_file(str(input_path), str(output_path))

    if result['success']:
        print(f"✓ Processed: {output_path}")
        if 'document_type' in result:
            print(f"  Document type: {result['document_type']}")
        if 'security_features_preserved' in result:
            print(f"  Features preserved: {', '.join(result['security_features_preserved'])}")
        if 'security_features_removed' in result:
            print(f"  Features removed: {', '.join(result['security_features_removed'])}")
    else:
        print(f"✗ Failed: {result.get('error', 'Unknown error')}")

    # Save JSON report if requested
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")


def cmd_batch(args):
    """Batch process multiple documents."""
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        raise SystemExit(f"Input directory not found: {input_dir}")

    # Load config if provided
    config = None
    if args.config:
        config_path = Path(args.config)
        if args.mode == 'security':
            config = SecurityDocumentConfig.from_yaml(config_path)
        elif args.mode == 'ocr-optimized':
            config = OCROptimizedConfig.from_yaml(config_path)
        else:
            config = ProcessingConfig.from_yaml(config_path)

    # Select preprocessor
    if args.mode == 'standard':
        preprocessor = DocumentPreprocessor(config)
    elif args.mode == 'security':
        preprocessor = SecurityDocumentPreprocessor(config)
    elif args.mode == 'ocr-optimized':
        preprocessor = OCROptimizedPreprocessor(config)
    else:
        raise SystemExit(f"Invalid mode: {args.mode}")

    # Process batch
    results = preprocessor.process_batch(str(input_dir), str(output_dir))

    # Print summary
    successful = sum(1 for r in results if r.get('success', False))
    print(f"\nBatch processing complete:")
    print(f"  Total: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(results) - successful}")

    # Save JSON report if requested
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")


def cmd_harness(args):
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")
    pdf_bytes = input_path.read_bytes()
    report = run_ocr_harness(pdf_bytes, lang=args.lang)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written to {args.json}")
    else:
        print(json.dumps(report, indent=2))


def build_parser():
    p = argparse.ArgumentParser(prog="autoocr", description="AutoOCR CLI - Production-grade document preprocessing")
    sub = p.add_subparsers(dest="command", required=True)

    # Original process command (kept for compatibility)
    p_proc = sub.add_parser("process", help="Run preprocessing pipeline on a PDF")
    p_proc.add_argument("input", help="Input PDF path")
    p_proc.add_argument("--out", help="Output processed PDF path")
    p_proc.add_argument("--json", help="Write JSON summary to file")
    p_proc.set_defaults(func=cmd_process)

    # New preprocess command with modes
    p_prep = sub.add_parser("preprocess", help="Preprocess document with mode selection")
    p_prep.add_argument("input", help="Input file path")
    p_prep.add_argument("output", help="Output file path")
    p_prep.add_argument("--mode",
                       choices=['standard', 'security', 'ocr-optimized'],
                       default='standard',
                       help="Processing mode: standard (default), security (preserve features), ocr-optimized (remove features)")
    p_prep.add_argument("--config", help="YAML config file path")
    p_prep.add_argument("--json", help="Write JSON report to file")
    p_prep.set_defaults(func=cmd_preprocess)

    # Batch processing command
    p_batch = sub.add_parser("batch", help="Batch process multiple documents")
    p_batch.add_argument("input_dir", help="Input directory")
    p_batch.add_argument("output_dir", help="Output directory")
    p_batch.add_argument("--mode",
                        choices=['standard', 'security', 'ocr-optimized'],
                        default='standard',
                        help="Processing mode")
    p_batch.add_argument("--config", help="YAML config file path")
    p_batch.add_argument("--json", help="Write JSON report to file")
    p_batch.set_defaults(func=cmd_batch)

    # Harness command
    p_harness = sub.add_parser("harness", help="Run OCR improvement harness")
    p_harness.add_argument("input", help="Input PDF path")
    p_harness.add_argument("--lang", default="eng", help="Tesseract language code")
    p_harness.add_argument("--json", help="Write harness report JSON path")
    p_harness.set_defaults(func=cmd_harness)

    return p


def main():  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
