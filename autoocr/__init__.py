"""autoocr package root.

Exposes high-level entry points and version info.
"""
from importlib.metadata import version, PackageNotFoundError

__all__ = ["__version__"]

try:
    __version__ = version("autoocr")
except PackageNotFoundError:  # running from source without install
    __version__ = "0.0.0+dev"
