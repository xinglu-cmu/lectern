"""Lectern — know what your AI is reading.

The engine is a pipeline of stages (DESIGN §4):

    load -> segment -> screen -> zone -> summarize -> emit

`analyze()` runs it end to end and returns an `Analysis`; the CLI (`lectern.cli`)
and the worker (`lectern_worker`) are two front doors onto that one function.
"""

from lectern.models import Analysis, Document, Finding, Segment, Zone
from lectern.pipeline import analyze

__version__ = "0.1.0"

# Bumped whenever the zone set or its definitions change (DESIGN §5). Every
# result carries it so labeled data and evals know which taxonomy they used.
TAXONOMY_V = "1"

__all__ = ["Analysis", "Document", "Finding", "Segment", "Zone", "analyze", "TAXONOMY_V"]
