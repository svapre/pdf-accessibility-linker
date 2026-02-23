import logging
import yaml
from typing import List, Optional

from data_models.schemas import SemanticReference, TargetNode

logger = logging.getLogger(__name__)

class EnterpriseResolver:
    """
    Phase 3: Relational Linker.
    Resolves SemanticReferences extracted in Phase 2 against the AST generated in Phase 1 
    and the topological YAML rulebook from Phase 0.
    """

    def __init__(self, ast: List[TargetNode], refs: List[SemanticReference], config_path: str):
        self.ast = ast
        self.refs = refs
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.page_map = self.config.get('page_map', [])
        # INVARIANT PROTECTED: Heuristic resolution is strictly decoupled from deterministic resolution.
        logger.warning("SYNTHETIC_RESOLUTION_DISABLED: Phase 3 currently operating in strict deterministic mode.")
        
    def _resolve_printed_to_physical(self, requested_logical: int, numbering_type: str) -> Optional[int]:
        """
        Converts a logical printed page number to an absolute physical page index.
        Enforces chronological first-match resolution for overlapping topology segments.
        """
        for seg in self.page_map:
            # INVARIANT PROTECTED: Roman numeral disambiguation using numbering_type
            if seg.get('numbering') != numbering_type:
                continue
                
            # INVARIANT PROTECTED: Inclusive <= bounds on both sides of segment lookup
            if seg['printed_start'] <= requested_logical <= seg['printed_end']:
                # INVARIANT PROTECTED: Printed -> physical conversion formula.
                # Because page_map is guaranteed chronologically sorted by Phase 0, 
                # the first matching segment correctly breaks ties (Header Dominance).
                return seg['physical_start'] + (requested_logical - seg['printed_start'])
                
        # INVARIANT PROTECTED: WARNING log on topology gap, no silent None return
        logger.warning(
            "TOPOLOGY_UNRESOLVED: Printed page %d (%s) falls outside all mapped segments.", 
            requested_logical, numbering_type
        )
        return None

    def _find_synthetic_page(self, short_anchor: str) -> Optional[int]:
        """
        Heuristic for finding a synthetic anchor page if AST lookup fails.
        Currently a stub. Downstream implementations would inject secondary text pass 
        or alias map resolution here.
        """
        return None

    def resolve(self) -> List[SemanticReference]:
        """
        Iterates through all mined references and attempts to attach a verified TargetNode.
        """
        resolved_refs = []
        
        # O(1) AST lookup optimization
        ast_dict = {node.target_id: node for node in self.ast}
        
        for ref in self.refs:
            urn = ref.short_anchor
            
            # --- 1. RESOLVE DIRECT PAGE LINKS ---
            if urn.startswith("page:"):
                parts = urn.split(":")
                if len(parts) != 3:
                    continue
                    
                _, num_type, val_str = parts
                val = int(val_str)
                
                target_phys = self._resolve_printed_to_physical(val, num_type)
                
                if target_phys is None:
                    logger.warning("DROPPED_REF: Target URN '%s' could not be mapped to a physical page (Source: %d).", urn, ref.source_page)
                    continue

                # INVARIANT PROTECTED: Populated only with fully valid TargetNode
                ref.resolved_target = TargetNode(
                    target_id=urn,
                    target_type="direct_page",
                    exact_name=urn,
                    page_number=target_phys,
                    confidence=1.0
                )
                ref.resolution_score = 1.0
                resolved_refs.append(ref)
                continue
            
            # --- 2. RESOLVE AST ASSETS & HIERARCHY ---
            # NOTE: Current Phase 1 Indexer produces simple URNs only (e.g., 'map:02').
            # Exact-match lookup is sufficient while indexing is flat. If the Indexer is updated to
            # produce compound semantic URNs (e.g., 'chapter:intro::map:02'), this line must be
            # updated to implement hierarchical suffix matching logic.
            matched_node = ast_dict.get(urn)
            
            if matched_node:
                ref.resolved_target = matched_node
                ref.resolution_score = matched_node.confidence * 1.0
                resolved_refs.append(ref)
            else:
                # --- 3. RESOLVE SYNTHETIC ANCHORS ---
                fallback_page = self._find_synthetic_page(urn)
                if fallback_page is not None:
                    # INVARIANT PROTECTED: Constructed as proper TargetNode, target_type="synthetic_asset", no duck-typing
                    ref.resolved_target = TargetNode(
                        target_id=urn,
                        target_type="synthetic_asset",
                        exact_name=f"Synthetic {urn}",
                        page_number=fallback_page,
                        confidence=0.5
                    )
                    ref.resolution_score = 0.5
                    resolved_refs.append(ref)
                else:
                    logger.warning("UNRESOLVED_ANCHOR: Target '%s' not found in AST and synthetic fallback failed.", urn)
        
        logger.info("Phase 3 Relational Linker complete. Successfully resolved %d of %d references.", len(resolved_refs), len(self.refs))
        return resolved_refs