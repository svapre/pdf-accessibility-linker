import fitz
import yaml
import re
import logging
from collections import defaultdict
from typing import List, Dict, Any
from data_models.schemas import TargetNode
from utils.canonical import CanonicalURN

logger = logging.getLogger(__name__)

class EnterpriseIndexer:
    """
    Phase 1: AST Builder.
    Consumes the deterministic YAML Rulebook from Phase 0 and strictly enforces
    its visual signatures against the physical PDF to build a flat list of TargetNodes (the AST).
    """

    def __init__(self, pdf_path: str, config_path: str):
        self.pdf_path = pdf_path
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.page_map = self.config.get('page_map', [])
        self.hierarchy = self.config.get('hierarchy_levels', [])
        self.assets = self.config.get('assets', [])

    def _is_in_valid_segment(self, physical_page: int) -> bool:
        """
        Validates physical page against the inclusive page_map bounds contract.
        Prevents indexing of elements that fall into physical dead zones (unmapped gaps).
        """
        for seg in self.page_map:
            # INVARIANT PROTECTED: physical_start <= p <= physical_end using <= on both sides
            if seg['physical_start'] <= physical_page <= seg['physical_end']:
                return True
        return False

    def _match_signature(self, size: float, is_bold: bool, signature: Dict[str, Any]) -> bool:
        """Deterministically matches a text span's geometry against a YAML visual signature."""
        fs = signature.get('font_size', {})
        min_v, max_v = fs.get('min', 0.0), fs.get('max', 999.0)
        
        if not (min_v <= size <= max_v):
            return False
            
        sig_bold = signature.get('is_bold', False)
        if sig_bold and not is_bold:
            return False
            
        return True

    def build_ast(self) -> List[TargetNode]:
        """
        Executes the single-pass AST construction.
        Guarantees no Gemini API calls or non-deterministic operations.
        """
        doc = fitz.open(self.pdf_path)
        nodes: List[TargetNode] = []
        counters: Dict[str, int] = defaultdict(int)
        pending_node = None
        pending_bbox = None
        
        try:
            for page_idx, page in enumerate(doc):
                # INVARIANT PROTECTED: TargetNode page_number must be 1-indexed absolute physical
                physical_page = page_idx + 1  
                
                # Enforce topology contract: ignore text on unmapped pages
                if not self._is_in_valid_segment(physical_page):
                    logger.debug("TOPOLOGY_GAP: Physical page %d falls outside mapped segments. Skipping.", physical_page)
                    continue
                    
                blocks = page.get_text("dict").get("blocks", [])
                for b in blocks:
                    if b['type'] != 0:
                        continue
                        
                    for line in b["lines"]:
                        if not line.get("spans"):
                            continue
                        
                        # Line-level aggregation to survive kerning splits
                        chars = "".join(s["text"] for s in line["spans"]).strip()
                        if not chars:
                            continue
                        
                        # Computes visual ink area as the geometric dominance proxy
                        primary_span = max(line["spans"], key=lambda s: (s["bbox"][2] - s["bbox"][0]) * s["size"])
                        size = primary_span["size"]
                        is_bold = "bold" in primary_span["font"].lower() or bool(primary_span["flags"] & 2**4)
                        
                        # Drop-cap rejection guard
                        if len(chars) < 3:
                            continue

                        # --- SPATIAL LOOKAHEAD BUFFER ---
                        if pending_node:
                            if abs(b['bbox'][1] - pending_bbox[3]) < 20 and size > 13.5:
                                pending_node.exact_name += ': ' + chars
                                pending_bbox = (
                                    pending_bbox[0], 
                                    pending_bbox[1], 
                                    max(pending_bbox[2], b['bbox'][2]), 
                                    b['bbox'][3]
                                )
                                continue
                            else:
                                nodes.append(pending_node)
                                pending_node = None
                                pending_bbox = None

                        # --- 1. MATCH ASSETS ---
                        asset_matched = False
                        for asset in self.assets:
                            if self._match_signature(size, is_bold, asset['visual_signature']):
                                m_type = asset['asset_type'].lower()
                                
                                # Enforce marker presence (e.g. text must actually contain 'Fig' or 'Map')
                                if re.search(rf'\b{m_type}\b', chars, re.I):
                                    # Namespacing prevents URN counter collisions between asset and hierarchy types
                                    counters[f"asset:{m_type}"] += 1
                                    
                                    # INVARIANT PROTECTED: Centralized authority for structural URN generation
                                    target_id = CanonicalURN.generate_structural_urn(m_type, counters[f"asset:{m_type}"])
                                    
                                    nodes.append(TargetNode(
                                        target_id=target_id,
                                        target_type="asset",
                                        exact_name=chars,
                                        page_number=physical_page,
                                        confidence=1.0
                                    ))
                                    asset_matched = True
                                    break
                                    
                        if asset_matched:
                            continue
                        
                        # --- 2. MATCH HIERARCHY ---
                        for lvl in self.hierarchy:
                            if self._match_signature(size, is_bold, lvl['visual_signature']):
                                # Extract semantic hypothesis from YAML to use as URN namespace
                                hyp_obj = lvl.get('label_hypothesis', {})
                                hyp = hyp_obj.get('preferred_label', 'theme')
                                conf = hyp_obj.get('confidence', 1.0)
                                
                                # INVARIANT PROTECTED: Slugification centralized in CanonicalURN utility
                                namespace = CanonicalURN.slugify(hyp)
                                
                                # Namespacing prevents URN counter collisions between asset and hierarchy types
                                counters[f"hier:{namespace}"] += 1
                                
                                # INVARIANT PROTECTED: Centralized authority for hierarchy URN generation
                                target_id = CanonicalURN.generate_structural_urn(namespace, counters[f"hier:{namespace}"])
                                
                                pending_node = TargetNode(
                                    target_id=target_id,
                                    target_type="hierarchy",
                                    exact_name=chars,
                                    page_number=physical_page,
                                    confidence=conf
                                )
                                pending_bbox = b['bbox']
                                break
                                
        finally:
            doc.close()
            
        if pending_node:
            nodes.append(pending_node)
            
        logger.info("Phase 1 AST Builder complete. Extracted %d TargetNodes.", len(nodes))
        return nodes