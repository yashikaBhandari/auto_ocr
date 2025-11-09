"""Pytest configuration: ensure project root and package are importable."""
import sys
from pathlib import Path

# Add project root (folder containing `autoocr`) if not present
root = Path(__file__).resolve().parents[2]
autoocr_dir = Path(__file__).resolve().parents[1]
for p in (str(root), str(autoocr_dir.parent)):
    if p not in sys.path:
        sys.path.insert(0, p)
