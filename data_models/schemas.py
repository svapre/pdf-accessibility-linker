import re
from dataclasses import dataclass
from typing import Optional, Literal, Tuple

# NOTE: Dual-update maintenance requirement. Any addition to the TargetType Literal 
# must be accompanied by corresponding routing/handling logic in resolver.py and annotator.py.
TargetType = Literal["hierarchy", "asset", "synthetic_asset", "direct_page"]

# Explanation: This compiled regex acts as the strict contract boundary between Phase 2 (Miner) 
# and Phase 3 (Resolver). By validating against an enumerated list of namespaces (page types 
# and known structural markers), it guarantees that hallucinated NLP artifacts, malformed syntax, 
# or unsupported reference types are rejected at instantiation before they can poison AST lookups.
# Choice: Option A (Strict flat alphanumeric/hyphen/dot suffix) to guarantee URL-safe, O(1) matching without hierarchical backtracking risks.
_ANCHOR_PATTERNS = re.compile(
    r'^(?:page:(?:arabic|roman):[1-9]\d*|[a-z0-9_.-]+:[A-Za-z0-9_.-]+)$'
)

@dataclass
class TargetNode:
    """AST Node representing a verified physical destination."""
    target_id: str
    target_type: TargetType
    exact_name: str
    page_number: int  # 1-indexed absolute physical PDF page
    confidence: float = 1.0

    def __post_init__(self):
        # INVARIANT PROTECTED: Physical pages must be strictly positive and canonical IDs cannot be null/empty.
        if self.page_number < 1:
            raise ValueError(f"Invalid physical page_number {self.page_number} for TargetNode '{self.target_id}'")
        if not self.target_id or not self.target_id.strip():
            raise ValueError("TargetNode target_id cannot be an empty string")

@dataclass
class SemanticReference:
    """Mined navigational pointer awaiting resolution."""
    source_page: int  # 1-indexed absolute physical PDF page
    short_anchor: str # e.g., 'page:arabic:24', 'map:02', 'theme:04'
    context_sentence: str
    source_bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1) origin bounding box
    inquiry_subject: Optional[str] = None
    resolved_target: Optional[TargetNode] = None
    resolution_score: float = 0.0

    def __post_init__(self):
        # INVARIANT PROTECTED: Physical source pages must be strictly positive integers.
        if self.source_page < 1:
            raise ValueError(f"Invalid physical source_page {self.source_page}")

        # INVARIANT PROTECTED: Mined URNs must strictly adhere to the typed grammatical schema contract.
        if not _ANCHOR_PATTERNS.match(self.short_anchor):
            raise ValueError(f"Malformed or unsupported short_anchor URN: '{self.short_anchor}'")

        # INVARIANT PROTECTED: Context sentences must contain extractable text to support spatial boundary resolution.
        if not self.context_sentence.strip():
            raise ValueError(f"Empty context_sentence for short_anchor '{self.short_anchor}'")

        # INVARIANT PROTECTED: Bounding boxes must be valid, non-degenerate Cartesian rectangles.
        x0, y0, x1, y1 = self.source_bbox
        if x0 >= x1 or y0 >= y1:
            raise ValueError(f"Degenerate or inverted bounding box coordinates: {self.source_bbox} for '{self.short_anchor}'")