import re
import logging
from typing import List, Tuple
from data_models.schemas import SemanticReference
from utils.canonical import CanonicalURN

logger = logging.getLogger(__name__)

class EnterpriseMiner:
    """
    Phase 2: Miner.
    Responsible for extracting navigational symbols (e.g., explicit page references) 
    from text spans and converting them into strict SemanticReference objects.
    """
    
    AMBIGUOUS_ROMAN_CHARS = frozenset({'c', 'd', 'l', 'm'})

    def __init__(self):
        # Strict validation patterns (Shared with Phase 0 Profiler)
        self.roman_validator = re.compile(r'^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$', re.IGNORECASE)
        # Capture group isolates the numeral/roman string
        self.page_pattern = re.compile(r'\b(?:page|p\.?)\s*([ivxlcdm]+|\d+)\b', re.IGNORECASE)

    def _get_match_bbox(self, page_object, match_text: str, context_bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """
        Retrieves the exact bounding box for the matched anchor text.
        Clips the search to the context sentence's bounding box to prevent duplicate instance collisions.
        """
        rects = page_object.search_for(match_text, clip=context_bbox)
        if rects:
            r = rects[0]
            return (r.x0, r.y0, r.x1, r.y1)
        
        # Fallback to the context bounding box if exact string layout shifts prevent a clean match
        logger.warning("BBOX_FALLBACK: Failed to extract exact bbox for anchor '%s' on page %d. Falling back to context bbox.", match_text, page_object.number + 1)
        return context_bbox

    def mine_page_references(self, page_num_0indexed: int, page_object, sent_text: str, sent_bbox: Tuple[float, float, float, float]) -> List[SemanticReference]:
        """
        Extracts explicit page references from a given sentence and constructs SemanticReferences.
        Expects a 0-indexed physical page number for strict boundary calculations.
        """
        assert page_num_0indexed >= 0, "page_num_0indexed must be a strictly positive integer or zero."
        
        refs = []
        for match in self.page_pattern.finditer(sent_text):
            full_match_text = match.group(0)
            token = match.group(1).lower()
            is_roman = not token.isdigit()

            if is_roman:
                # Guard against ambiguous single-character artifacts. 'i', 'v', 'x' are retained as valid 
                # single-digit Roman page references since they follow a strict 'page'/'p.' prefix.
                if len(token) == 1 and token in self.AMBIGUOUS_ROMAN_CHARS:
                    continue
                if not bool(self.roman_validator.match(token)):
                    continue

            val = int(token) if not is_roman else self._roman_to_int(token)
            if val <= 0:
                continue

            num_type = "roman" if is_roman else "arabic"
            
            # INVARIANT PROTECTED: Centralized authority for URN formatting to prevent routing drift.
            urn_symbol = CanonicalURN.generate_page_urn(val, num_type)
            
            source_bbox = self._get_match_bbox(page_object, full_match_text, sent_bbox)

            ref = SemanticReference(
                source_page=page_num_0indexed + 1,  # 1-indexed absolute physical page
                short_anchor=urn_symbol,
                context_sentence=sent_text.strip(),
                source_bbox=source_bbox
            )
            refs.append(ref)
        return refs

    def _roman_to_int(self, s: str) -> int:
        """Deterministic conversion of validated Roman numerals."""
        roman_map = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
        total, prev = 0, 0
        for ch in reversed(s):
            val = roman_map.get(ch, 0)
            total += -val if val < prev else val
            prev = val
        return total