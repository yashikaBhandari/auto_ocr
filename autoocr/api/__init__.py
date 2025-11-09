"""API package root.

Keep imports minimal to avoid circular dependencies during test collection.
Submodules (`main`, `pipeline`, `modules`, `utils`) are available via
standard Python import (e.g. `from autoocr.api.pipeline import Pipeline`).
"""

__all__: list[str] = []
