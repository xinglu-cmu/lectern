"""`zone`: give every segment a functional role (DESIGN §5).

Two passes. `heuristics` labels the easy majority for free and offline —
page furniture, code, detector hits, sections whose heading says what they
are, text dense with imperatives. `llm_pass` then asks Claude Haiku about the
segments the heuristics were unsure of (confidence below `LLM_THRESHOLD`),
with the document text passed as quoted data and the answer constrained by a
schema. Cost therefore scales with how ambiguous a document is, not how long.
"""

from lectern.zoning.heuristics import zone_heuristics
from lectern.zoning.llm_pass import LLM_THRESHOLD, zone_with_llm

__all__ = ["zone_heuristics", "zone_with_llm", "LLM_THRESHOLD"]
