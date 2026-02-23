import fitz
import logging
import os
from typing import List
from data_models.schemas import SemanticReference

logger = logging.getLogger(__name__)

class EnterpriseAnnotator:
    """
    Phase 4: Binary Rewriter.
    Terminal phase responsible for mutating the PDF binary by injecting deterministic 
    LINK_GOTO annotations based on resolved semantic references.
    """

    def __init__(self, pdf_path: str, output_path: str, debug_mode: bool = False, min_confidence: float = 0.75):
        self.pdf_path = pdf_path
        self.output_path = output_path
        self.debug_mode = debug_mode
        self.min_confidence = min_confidence
        # Use established PyMuPDF link kind constant
        self.link_kind = fitz.LINK_GOTO

    def annotate(self, resolved_refs: List[SemanticReference]) -> bool:
        """
        Executes the binary annotation pass.
        Guarantees transactional integrity: the output file is only written 
        if all annotations are successfully processed.
        """
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"Source PDF not found: {self.pdf_path}")

        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        applied_count = 0

        try:
            for ref in resolved_refs:
                # INVARIANT PROTECTED: resolved_target must be non-None. 
                # Skip unresolved references without polluting the binary.
                if ref.resolved_target is None:
                    logger.warning("ANNOTATION_SKIPPED: Reference '%s' on page %d was not resolved.", ref.short_anchor, ref.source_page)
                    continue

                if getattr(ref, 'resolution_score', 0.0) < self.min_confidence:
                    logger.warning("ANNOTATION_DROPPED: Score %.2f below threshold (%.2f) for '%s'.", getattr(ref, 'resolution_score', 0.0), self.min_confidence, ref.short_anchor)
                    continue

                source_page_idx = ref.source_page - 1
                target_page_idx = ref.resolved_target.page_number - 1

                # INVARIANT PROTECTED: Out-of-bounds page numbers produce a loud failure.
                if not (0 <= source_page_idx < total_pages):
                    raise IndexError(f"Source page {ref.source_page} is out of document bounds (Total: {total_pages}).")
                
                if not (0 <= target_page_idx < total_pages):
                    raise IndexError(f"Target page {ref.resolved_target.page_number} for URN '{ref.resolved_target.target_id}' is out of document bounds.")

                page = doc[source_page_idx]

                # INVARIANT PROTECTED: source_bbox from locked schema used directly as the link rectangle.
                # No search_for() calls allowed here to prevent duplicate-text collisions.
                link_rect = fitz.Rect(ref.source_bbox)

                # INVARIANT PROTECTED: fitz.LINK_GOTO kind used correctly with 0-indexed destination.
                link_data = {
                    "kind": self.link_kind,
                    "from": link_rect,
                    "page": target_page_idx,
                    "zoom": 0 # Maintain current zoom level on jump
                }

                page.insert_link(link_data)
                
                if self.debug_mode:
                    page.draw_rect(link_rect, color=(1, 0, 0), width=1.5)
                    
                applied_count += 1

            # Garbage=3 removes all unused objects; deflate=True compresses stream data for production-grade output.
            doc.save(self.output_path, garbage=3, deflate=True)
            logger.info("Phase 4 Annotator complete. Injected %d hyperlinks into %s.", applied_count, self.output_path)
            return True

        except (IndexError, ValueError) as e:
            logger.error("ANNOTATION_BOUNDS_FAULT: %s No output written.", str(e))
            raise
        except Exception as e:
            logger.error("CRITICAL_ANNOTATION_FAILURE: %s No output written.", str(e))
            raise
        finally:
            doc.close()