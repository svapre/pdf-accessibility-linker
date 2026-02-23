import os
import fitz
import yaml
import statistics
import glob
import re
import logging
import math
import string
from collections import defaultdict, Counter
from typing import List, Dict, Optional
from datetime import datetime

from core.vocabulary_registry import VocabularyRegistry
logger = logging.getLogger(__name__)

# --- COMPILER UTILITIES & CONSTANTS ---
ROMAN_VALIDATOR = re.compile(r'^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$', re.IGNORECASE)
ROMAN_MAP = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}

def is_valid_roman(s: str) -> bool:
    """Strict regex validation to prevent heuristic hallucination of numerals."""
    return bool(ROMAN_VALIDATOR.match(s.strip()))

def roman_to_int(s: str) -> int:
    """Deterministic conversion of validated Roman numerals."""
    s = s.lower().strip()
    total, prev = 0, 0
    for ch in reversed(s):
        val = ROMAN_MAP.get(ch, 0)
        total += -val if val < prev else val
        prev = val
    return total

class EnterpriseProfiler:
    """
    Phase 0: Grammar Inducer.
    Induces a document's visual grammar and topology using geometric invariants.
    """
    MAX_HEADER_AVG_PER_PAGE = 3.5
    MAX_ASSET_MARKERS_PER_PAGE = 3.0
    HEADER_MARGIN_RATIO = 0.15 
    FOOTER_MARGIN_RATIO = 0.85 

    def __init__(self, pdf_path: str, api_key: Optional[str] = None, model_name: str = "gemini-3-flash-preview", doc_name: str = "unknown_doc", mode: str = "full", vocab_override: Optional[str] = None, app_settings: Optional[Dict] = None):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.api_key = api_key
        self.model_name = model_name
        self.doc_name = doc_name
        self.mode = mode
        self.vocab_override = vocab_override
        self.app_settings = app_settings or {}
        self.total_pages = len(self.doc)
        self.cluster_scan_limit = min(self.app_settings.get('pipeline_tuning', {}).get('cluster_scan_limit', self.total_pages), self.total_pages)
        self.topo_scan_limit = min(self.app_settings.get('pipeline_tuning', {}).get('topo_scan_limit', self.total_pages), self.total_pages)
        self.grid_size = self._calculate_adaptive_grid()

    def _calculate_adaptive_grid(self) -> float:
        """Determines visual granularity using a stratified sample."""
        samples = []
        sample_pages = [int(i * (self.total_pages - 1) / 9) for i in range(min(10, self.total_pages))]
        
        for p in sample_pages:
            for b in self.doc[p].get_text("dict").get("blocks", []):
                if b['type'] == 0:
                    for line in b["lines"]:
                        for span in line["spans"]:
                            samples.append(span["size"])
        
        unique_sorted = sorted(list(set(samples)))
        deltas = [unique_sorted[i+1] - unique_sorted[i] for i in range(len(unique_sorted)-1) if unique_sorted[i+1] - unique_sorted[i] > 0.05]
        return max(0.1, min(0.25, statistics.median(deltas) if deltas else 0.1))

    def _compute_content_weight(self, page_idx: int, body_size: float) -> float:
        blocks = self.doc[page_idx].get_text("dict").get("blocks", [])
        char_count = 0
        block_count = 0
        font_proximity_scores = []
        for b in blocks:
            if b['type'] != 0: continue
            block_count += 1
            for line in b["lines"]:
                for span in line["spans"]:
                    char_count += len(span["text"].strip())
                    if span["size"] > 0:
                        font_proximity_scores.append(
                            1.0 / (1.0 + abs(span["size"] - body_size))
                        )
        avg_font_proximity = statistics.mean(font_proximity_scores) if font_proximity_scores else 0.0
        return (char_count * 0.6) + (block_count * 10) + (avg_font_proximity * 30)

    def _validate_and_correct_api_response(self, raw_response: Dict) -> Optional[Dict]:
        """
        Implements three-tier validation for AI responses:
        Tier 1: Schema validation (auto-correct)
        Tier 2: Semantic consistency (auto-correct)
        Tier 3: Retry trigger (unrecoverable errors)
        """
        if not raw_response or not isinstance(raw_response, dict):
            return None

        # Tier 1: Schema Validation
        if not raw_response.get('primary_marker'):
            raw_response['primary_marker'] = "Chapter"
            logger.warning("SCHEMA_CORRECTION: primary_marker missing, defaulted to Chapter.")
        
        if not isinstance(raw_response.get('chapter_count'), int) or raw_response.get('chapter_count', 0) <= 0:
            raw_response['chapter_count'] = 0
            logger.warning("SCHEMA_CORRECTION: chapter_count invalid.")

        if not raw_response.get('layout_templates') or not isinstance(raw_response.get('layout_templates'), list):
            logger.error("SCHEMA_UNRECOVERABLE: layout_templates missing.")
            return None

        valid_templates = []
        allowed_sizes = self.app_settings.get('pipeline_tuning', {}).get('allowed_relative_sizes', ['medium'])

        for idx, tmpl in enumerate(raw_response['layout_templates']):
            if not tmpl.get('template_id'):
                tmpl['template_id'] = f"template_{idx}"
            
            if not isinstance(tmpl.get('is_chapter_opener'), bool):
                tmpl['is_chapter_opener'] = False
            
            if not tmpl.get('elements') or not isinstance(tmpl.get('elements'), list):
                logger.warning("SCHEMA_CORRECTION: template %s had no elements, removed.", tmpl['template_id'])
                continue
            
            for el in tmpl['elements']:
                if not el.get('role'): el['role'] = "unknown"
                if el.get('relative_size') not in allowed_sizes:
                    logger.warning("SCHEMA_CORRECTION: invalid relative_size %s corrected to medium.", el.get('relative_size'))
                    el['relative_size'] = "medium"
                if not isinstance(el.get('repeats_on_page'), int) or el.get('repeats_on_page', 0) < 1:
                    el['repeats_on_page'] = 1
                if not el.get('example_text'): el['example_text'] = ""
            
            valid_templates.append(tmpl)
        
        raw_response['layout_templates'] = valid_templates
        if not valid_templates:
            return None

        if not isinstance(raw_response.get('non_chapter_markers'), list):
            raw_response['non_chapter_markers'] = []
        if not isinstance(raw_response.get('compound_titles'), list):
            raw_response['compound_titles'] = []
        if not isinstance(raw_response.get('font_role_map'), list):
            raw_response['font_role_map'] = []

        # Tier 2: Semantic Consistency
        opener_count = sum(1 for t in valid_templates if t['is_chapter_opener'])
        
        if opener_count == 0:
            # Inference heuristic
            for t in valid_templates:
                if any(r in el['role'] for el in t['elements'] for r in ['chapter_marker', 'chapter_number', 'chapter_title']):
                    t['is_chapter_opener'] = True
                    logger.warning("SCHEMA_CORRECTION: inferred is_chapter_opener from element roles.")
                    break
            # Fallback to largest element heuristic if still 0 (omitted for brevity, relies on relative_size order)
        elif opener_count > 1:
            first_found = False
            for t in valid_templates:
                if t['is_chapter_opener']:
                    if first_found: t['is_chapter_opener'] = False
                    else: first_found = True
            logger.warning("SCHEMA_CORRECTION: multiple chapter openers detected, kept first.")

        return raw_response

    def _build_base_prompt(self, cluster_info: dict, n_clusters: int) -> str:
        """Constructs the AI layout schema prompt. Single source of truth for both API and manual review paths."""
        return (
            'You are analyzing a representative sample of pages from a textbook PDF.\n'
            'These pages were algorithmically selected to show the DISTINCT LAYOUT TEMPLATES '
            'this book uses. They are intentionally diverse and do NOT represent how the '
            'entire book looks. Each page represents a different structural template.\n\n'
            f'Document has {self.total_pages} total pages.\n'
            f'Font clusters detected (size -> avg occurrences/page): {cluster_info}\n'
            f'Distinct layout templates found by clustering: {n_clusters}\n\n'
            'Your task: identify the structural vocabulary and describe the layout schema '
            'of each template. Look for the template that functions as the chapter/section '
            'opener — it will contain the largest font text, appear at regular intervals, '
            'and introduce a new major section.\n\n'
            'IMPORTANT: If any text appears in the same large-font cluster as the chapter '
            'marker but does NOT introduce a chapter (e.g. TIMELINE, APPENDIX, CONCLUSION, '
            'PREFACE), you MUST list it in the non_chapter_markers array with the correct reason.\n\n'
            'Return ONLY a valid JSON object with no explanation or markdown:\n'
            '{\n'
            '  "primary_marker": "single word for top-level divisions e.g. Theme/Chapter/Part/Unit",\n'
            '  "chapter_count": <integer>,\n'
            '  "layout_templates": [\n'
            '    {\n'
            '      "template_id": "descriptive_snake_case_id",\n'
            '      "is_chapter_opener": <true or false>,\n'
            '      "elements": [\n'
            '        {\n'
            '          "role": "descriptive role e.g. chapter_marker/chapter_number/chapter_title/section_label/body_text",\n'
            '          "relative_size": "one of: small/medium/large/very_large/giant",\n'
            '          "position": "descriptive e.g. top_left_box/center/right_of_box/below_label",\n'
            '          "repeats_on_page": <integer>,\n'
            '          "example_text": "exact text from the page"\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  ],\n'
            '  "non_chapter_markers": [\n'
            '    {\n'
            '      "text_pattern": "exact text that appears in same font cluster as chapter marker but is NOT a chapter",\n'
            '      "reason": "one of: reference_insert/section_grouper/running_header/decorative",\n'
            '      "appears_in_same_cluster_as": "role name from layout_templates elements"\n'
            '    }\n'
            '  ],\n'
            '  "compound_titles": [{"marker": "Theme 1", "title": "From the Beginning of Time"}],\n'
            '  "font_role_map": [{"font_size_approx": 100, "role": "chapter_label"}]\n'
            '}'
        )

    def _extract_structural_vocabulary(self, slots: Dict, clusters: Dict, body_size: float) -> Dict:
        """
        Priority chain: Registry -> Gemini API -> Manual Review Packet.
        """
        # 0. CLI Override
        if self.mode == 'override':
            marker = self.vocab_override if self.vocab_override else "Chapter"
            logger.info("VOCAB_RESOLUTION for '%s'\n  Path taken    : cli_override\n  Source        : cli_override\n  Result        : primary=%s confidence=1.0\n  [if cli_override]: Runtime only. Use ingest_vocabulary.py to persist.", self.doc_name, marker)
            return {'primary_marker': marker, 'source': 'cli_override', 'confidence': 1.0}

        registry = VocabularyRegistry()
        manual_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "manual_review")
        if not os.path.exists(manual_dir):
            os.makedirs(manual_dir)

        # 0.5 Auto-ingest Manual Responses
        manual_ingested = False
        response_files = glob.glob(os.path.join(manual_dir, "*_response.json"))
        for rf in response_files:
            try:
                with open(rf, 'r') as f:
                    data = json.load(f)
                
                entries = data if isinstance(data, list) else [data]
                batch_processed = True
                
                for entry in entries:
                    if entry.get('doc_name') == self.doc_name:
                        required = ['primary_marker', 'chapter_count', 'compound_titles', 'font_role_map']
                        if all(k in entry for k in required):
                            registry.write_manual_result(self.doc_name, entry)
                            logger.info("MANUAL_VOCAB_AUTO_INGESTED: doc=%s primary=%s", self.doc_name, entry['primary_marker'])
                            manual_ingested = True
                            
                            # Clear pending flag
                            flag_path = os.path.join(manual_dir, f"{self.doc_name}_pending.flag")
                            if os.path.exists(flag_path):
                                os.remove(flag_path)
                
                # Check if we can delete the batch file
                if isinstance(data, list):
                    for entry in entries:
                        d_name = entry.get('doc_name')
                        if os.path.exists(os.path.join(manual_dir, f"{d_name}_pending.flag")):
                            batch_processed = False
                    if batch_processed:
                        os.remove(rf)
                elif manual_ingested: # Single file legacy
                    os.remove(rf)
                    
            except Exception as e:
                logger.warning("AUTO_INGEST_ERROR: %s", str(e))
        
        # 1. Unsupervised Typographic Clustering
        # Reconstruct page vectors from slots
        page_stats = defaultdict(lambda: {'giant': 0, 'large': 0, 'medium': 0, 'body': 0, 'total': 0})
        
        # Load thresholds from settings
        tuning = self.app_settings.get('pipeline_tuning', {})
        t_giant = tuning.get('vector_giant_threshold', 3.0)
        t_large = tuning.get('vector_large_threshold', 1.8)
        t_medium = tuning.get('vector_medium_threshold', 1.1)
        
        for grid_idx, obs_list in slots.items():
            for obs in obs_list:
                p_idx = obs['page'] - 1 # 0-indexed
                if p_idx >= self.cluster_scan_limit: continue
                
                size = obs['size']
                chars = obs['chars']
                
                if size > body_size * t_giant:
                    cat = 'giant'
                elif size > body_size * t_large:
                    cat = 'large'
                elif size > body_size * t_medium:
                    cat = 'medium'
                else:
                    cat = 'body'
                
                page_stats[p_idx][cat] += chars
                page_stats[p_idx]['total'] += chars

        page_vectors = {}
        for p in range(self.cluster_scan_limit):
            # Compute image flag
            has_image = 0.0
            try:
                for b in self.doc[p].get_text("dict").get("blocks", []):
                    if b['type'] != 0:
                        has_image = 1.0
                        break
            except Exception:
                pass

            stats = page_stats[p]
            total = stats['total']
            if total == 0:
                page_vectors[p] = (0.0, 0.0, 0.0, 0.0, has_image)
            else:
                page_vectors[p] = (
                    stats['giant'] / total,
                    stats['large'] / total,
                    stats['medium'] / total,
                    stats['body'] / total,
                    has_image
                )

        # Euclidean Clustering
        typo_clusters = [] # List of {'centroid': tuple, 'pages': list}
        DISTANCE_THRESHOLD = self.app_settings.get('pipeline_tuning', {}).get('clustering_distance_threshold', 0.10)

        for p in range(self.cluster_scan_limit):
            vec = page_vectors[p]
            best_dist = float('inf')
            best_cluster_idx = -1
            
            for i, c in enumerate(typo_clusters):
                centroid = c['centroid']
                dist = math.sqrt(sum((v - c_val) ** 2 for v, c_val in zip(vec, centroid)))
                if dist < best_dist:
                    best_dist = dist
                    best_cluster_idx = i
            
            if best_dist < DISTANCE_THRESHOLD:
                # Add to existing cluster
                c = typo_clusters[best_cluster_idx]
                c['pages'].append(p)
                # Recalculate centroid (moving average)
                n = len(c['pages'])
                c['centroid'] = tuple(
                    (c_val * (n - 1) + v) / n 
                    for c_val, v in zip(c['centroid'], vec)
                )
            else:
                # Create new cluster
                typo_clusters.append({'centroid': vec, 'pages': [p]})

        # Sort by size (descending)
        typo_clusters.sort(key=lambda x: len(x['pages']), reverse=True)

        # Select Representative Pages
        selected_pages = []
        
        # Pass 1: One from each of top 8 clusters
        for c in typo_clusters[:8]:
            # Pick page closest to centroid
            centroid = c['centroid']
            best_p = c['pages'][0]
            min_d = float('inf')
            for p in c['pages']:
                v = page_vectors[p]
                d = math.sqrt(sum((x-y)**2 for x,y in zip(v, centroid)))
                if d < min_d:
                    min_d = d
                    best_p = p
            selected_pages.append(best_p)

        # Pass 2: Fill if < 8
        if len(selected_pages) < 8:
            needed = 8 - len(selected_pages)
            candidates = []
            for c in typo_clusters:
                centroid = c['centroid']
                sorted_pages = sorted(c['pages'], key=lambda p: math.sqrt(sum((x-y)**2 for x,y in zip(page_vectors[p], centroid))))
                for p in sorted_pages:
                    if p not in selected_pages:
                        candidates.append(p)
            selected_pages.extend(candidates[:needed])

        selected_pages.sort()
        centroids = [tuple(round(x, 2) for x in c['centroid']) for c in typo_clusters]
        logger.debug("TYPO_CLUSTERING: Scanned %d pages, found %d clusters. Selected: %s. Cluster centroids: %s", 
                     self.cluster_scan_limit, len(typo_clusters), selected_pages, centroids)
        
        # Collect text samples from top clusters for validation
        validation_samples = []
        for idx, c in clusters.items():
            if c['center'] > body_size * 1.5:
                validation_samples.extend(c['samples'])

        top_clusters = sorted(clusters.items(), key=lambda x: x[1]['center'], reverse=True)[:8]
        cluster_info = {round(v['center'], 1): round(v['avg_per_page'], 1) for k, v in top_clusters}
        base_prompt = self._build_base_prompt(cluster_info, len(typo_clusters))

        def validator_fn(entry: Dict) -> bool:
            marker = entry.get('primary_marker')
            if not marker:
                return False
            # Check if marker appears in top cluster samples (case-insensitive)
            marker_lower = marker.lower()
            for sample in validation_samples:
                if marker_lower in sample.lower():
                    return True
            return False

        # 2. Registry Lookup
        hit = registry.get(self.doc_name, validator_fn, top_cluster_samples=validation_samples)
        
        # Manual-Only Mode Gate
        if self.mode == 'manual-only':
            if hit and hit['source'] == 'manual_ingest':
                logger.info("VOCAB_RESOLUTION for '%s'\n  Path taken    : manual_auto_ingested\n  Source        : manual_ingest\n  Result        : primary=%s confidence=%.2f\n  [if manual_auto_ingested]: File cleared. Registry updated.", self.doc_name, hit['primary_marker'], hit['confidence'])
                return hit
            else:
                logger.error("VOCAB_REQUIRED: Document halted in manual-only mode.")
                raise RuntimeError("VOCAB_REQUIRED: No manual entry found for " + self.doc_name)

        if hit and hit['source'] in ['manual_ingest', 'gemini_api']:
            path_taken = 'manual_auto_ingested' if manual_ingested else 'registry_hit'
            extra_msg = ""
            if path_taken == 'manual_auto_ingested':
                extra_msg = "\n  File cleared. Registry updated."
            elif path_taken == 'registry_hit':
                extra_msg = f"\n  Timestamp     : {hit['timestamp']}"
            
            logger.info("VOCAB_RESOLUTION for '%s'\n  Path taken    : %s\n  Source        : %s\n  Result        : primary=%s confidence=%.2f%s", 
                        self.doc_name, path_taken, hit['source'], hit['primary_marker'], hit['confidence'], extra_msg)
            return hit

        # 3. API Call (skipped if no-api or offline)
        if self.mode not in ['no-api', 'offline'] and self.api_key:
            try:
                from google import genai
                from google.genai import types
                
                temp_doc = fitz.open()
                try:
                    for p_idx in selected_pages:
                        temp_doc.insert_pdf(self.doc, from_page=p_idx, to_page=p_idx)
                    pdf_bytes = temp_doc.write()
                finally:
                    temp_doc.close()

                client = genai.Client(api_key=self.api_key)
                
                max_retries = self.app_settings.get('pipeline_tuning', {}).get('api_retry_attempts', 1)
                current_prompt = base_prompt
                
                for attempt in range(max_retries + 1):
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[current_prompt, types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf')]
                    )
                    
                    text = response.text.strip()
                    if text.startswith("```json"): text = text[7:-3].strip()
                    elif text.startswith("```"): text = text[3:-3].strip()
                    
                    import json
                    raw_result = json.loads(text)
                    validated_result = self._validate_and_correct_api_response(raw_result)
                    
                    if validated_result:
                        validated_result['confidence'] = 0.95
                        registry.write_api_result(self.doc_name, validated_result)
                        logger.info("VOCAB_RESOLUTION for '%s'\n  Path taken    : api_success\n  Source        : gemini_api\n  Result        : primary=%s confidence=%.2f", self.doc_name, validated_result.get('primary_marker'), validated_result.get('confidence'))
                        return validated_result
                    
                    logger.warning("API_RETRY: Attempt %d of %d due to validation failure.", attempt + 1, max_retries)
                    current_prompt = base_prompt + "\n\nPrevious response failed validation: layout_templates was empty or missing. Ensure layout_templates is a non-empty array with at least one entry, and that exactly one template has is_chapter_opener set to true."

            except Exception as e:
                logger.warning("STRUCTURAL_VOCAB_API_FAIL: %s", str(e))
        
        # 4. Manual Review Packet (Fallback)
        if self.mode != 'offline':
            # Generate per-document packet
            packet_pdf = os.path.join(manual_dir, f"{self.doc_name}_pages.pdf")
            packet_txt = os.path.join(manual_dir, f"{self.doc_name}_prompt.txt")
            
            try:
                temp_doc = fitz.open()
                for p_idx in selected_pages:
                    temp_doc.insert_pdf(self.doc, from_page=p_idx, to_page=p_idx)
                temp_doc.save(packet_pdf)
                temp_doc.close()
                
                prompt_text = base_prompt + (
                    f'\n\nFiles to attach: {self.doc_name}_pages.pdf\n'
                    f'Save your response as config/manual_review/{self.doc_name}_response.json then rerun the pipeline.'
                )
                
                with open(packet_txt, 'w') as f:
                    f.write(prompt_text)
                    
                # Write pending flag
                with open(os.path.join(manual_dir, f"{self.doc_name}_pending.flag"), 'w') as f:
                    f.write(f"{self.doc_name}\n{datetime.now().isoformat()}")
                    
                # Regenerate Batch Prompts
                pending_flags = sorted(glob.glob(os.path.join(manual_dir, "*_pending.flag")))
                batches = [pending_flags[i:i + 3] for i in range(0, len(pending_flags), 3)]
                
                for i, batch in enumerate(batches):
                    batch_num = i + 1
                    batch_docs = []
                    batch_files = []
                    for flag in batch:
                        d_name = os.path.basename(flag).replace("_pending.flag", "")
                        batch_docs.append(d_name)
                        batch_files.append(f"{d_name}_pages.pdf")
                    
                    batch_prompt = (
                        f"You will be given {len(batch)} PDF files, one per document. Analyze each INDEPENDENTLY.\n"
                        "Return ONLY a JSON array, one object per document, in the SAME ORDER as files provided.\n"
                        "Each object must include \"doc_name\" matching the filename exactly.\n\n"
                        "[\n"
                        "  {\n"
                        "    \"doc_name\": \"exact_filename_without_extension\",\n"
                        "    ... (same schema as above) ...\n"
                        "  },\n"
                        "  ...\n"
                        "]\n\n"
                        "Use the following schema for each document object:\n"
                        f"{base_prompt}\n\n"
                        f"Files to attach for this batch: {', '.join(batch_files)}\n"
                        f"Save your response as config/manual_review/batch_{batch_num}_response.json then rerun the pipeline."
                    )
                    
                    with open(os.path.join(manual_dir, f"batch_{batch_num}_prompt.txt"), 'w') as f:
                        f.write(batch_prompt)
                
                logger.warning("MANUAL_REVIEW_REQUIRED: Packet written to %s. Batch prompts updated.", packet_pdf)
            
            except Exception as e:
                logger.error("MANUAL_PACKET_FAIL: %s", str(e))

        # Log Fallback
        path_taken = hit['source']
        extra_msg = ""
        if path_taken == 'default_fallback':
            packet_path = os.path.join(manual_dir, f"{self.doc_name}_pages.pdf")
            extra_msg = f"\n  Packet        : {packet_path}. Save AI response as batch_N_response.json and rerun."
        elif path_taken == 'statistical_fallback':
            extra_msg = "\n  Note          : Low confidence. Consider manual review."

        logger.info("VOCAB_RESOLUTION for '%s'\n  Path taken    : %s\n  Source        : %s\n  Result        : primary=%s confidence=%.2f%s", 
                    self.doc_name, path_taken, hit['source'], hit['primary_marker'], hit['confidence'], extra_msg)

        return hit

    def run(self) -> Dict:
        try:
            # --- 1. DETERMINISTIC DATA COLLECTION ---
            slots = defaultdict(list)
            topo_candidates = defaultdict(list)
            
            for p_idx in range(self.topo_scan_limit):
                page = self.doc[p_idx]
                h_zone = page.rect.height * self.HEADER_MARGIN_RATIO
                f_zone = page.rect.height * self.FOOTER_MARGIN_RATIO
                
                for b in page.get_text("dict").get("blocks", []):
                    if b['type'] != 0: continue
                    for line in b["lines"]:
                        ink_width = sum((s["bbox"][2] - s["bbox"][0]) for s in line["spans"])
                        ink_area = ink_width * (line["bbox"][3] - line["bbox"][1])
                        
                        chars = " ".join(s["text"].strip() for s in line["spans"] if s["text"].strip()).strip()
                        if not chars: continue

                        primary_span = max(line["spans"], key=lambda s: (s["bbox"][2] - s["bbox"][0]) * s["size"])
                        raw_size = primary_span["size"]
                        
                        grid_idx = int(raw_size // self.grid_size)
                        y_mid = (line["bbox"][1] + line["bbox"][3]) / 2
                        
                        if p_idx < self.cluster_scan_limit:
                            slots[grid_idx].append({
                                'size': raw_size,
                                'chars': len(chars),
                                'area': ink_area,
                                'is_bold': "bold" in primary_span["font"].lower() or primary_span["flags"] & 2**4,
                                'page': p_idx + 1, # 1-indexed physical page
                                'text': chars,
                                'y': y_mid,
                                'x': line["bbox"][0]
                            })

                        if y_mid <= h_zone or y_mid >= f_zone:
                            y_band_label = "header" if y_mid <= h_zone else "footer"
                            
                            for m in re.finditer(r'\b([ivxlcdm]{1,10})\b', chars.lower()):
                                token = m.group(1)
                                if is_valid_roman(token):
                                    val = roman_to_int(token)
                                    if 0 < val <= self.total_pages * 2:
                                        topo_candidates[p_idx + 1].append({
                                            'val': val, 'y': y_mid, 'x': line["bbox"][0],
                                            'grid_idx': grid_idx, 'type': 'roman',
                                            'text_len': len(token),
                                            'raw_size': raw_size,
                                            'y_band_label': y_band_label
                                        })
                            
                            for m in re.finditer(r'(?<!\d)(\d{1,4})(?!\d)', chars.lower()):
                                token = m.group(1)
                                val = int(token)
                                if 0 < val <= self.total_pages * 2:
                                    topo_candidates[p_idx + 1].append({
                                        'val': val, 'y': y_mid, 'x': line["bbox"][0],
                                        'grid_idx': grid_idx, 'type': 'arabic',
                                        'text_len': len(token),
                                        'raw_size': raw_size,
                                        'y_band_label': y_band_label
                                    })

            if not slots:
                raise RuntimeError("CRITICAL: No extractable text detected. PDF may be an image-only scan.")

            # --- 2. CLUSTER REDUCTION ---
            clusters = {}
            for idx, obs in slots.items():
                center = statistics.median([o['size'] for o in obs])
                pages = set(o['page'] for o in obs)
                clusters[idx] = {
                    'center': center,
                    'coverage': len(pages) / self.cluster_scan_limit,
                    'unique_pages': len(pages),
                    'density': sum(o['chars'] for o in obs) / max(sum(o['area'] for o in obs), 0.001),
                    'bold_ratio': sum(1 for o in obs if o['is_bold']) / len(obs),
                    'avg_per_page': len(obs) / len(pages),
                    'markers': {m: sum(1 for o in obs if re.search(rf'\b{m}\b', o['text'], re.I)) for m in ['Fig', 'Map', 'Table']},
                    'samples': [o['text'] for o in obs[:10]]
                }

            # --- 3. SELECTION ---
            body_idx = max(clusters.keys(), key=lambda k: (clusters[k]['coverage'] * clusters[k]['density']) / (1 + clusters[k]['bold_ratio']))
            body_size = clusters[body_idx]['center']

            # --- 3.5 STRUCTURAL VOCABULARY ---
            struct_vocab = self._extract_structural_vocabulary(slots, clusters, body_size)
            logger.info("STRUCTURAL_VOCAB: Primary='%s' (%.2f)",
                        struct_vocab.get('primary_marker'), struct_vocab.get('confidence', 0.0))

            # --- 4. TOPOLOGY MAPPING (DAG Longest Path Sequence Induction) ---
            streams = defaultdict(list)
            for p, cands in topo_candidates.items():
                for c in cands:
                    c['p'] = p
                    c['offset'] = p - c['val']
                    stream_key = (c['type'], c['y_band_label'])
                    streams[stream_key].append(c)
            
            best_score = -1
            target_stream_key = None
            winning_chain = []

            for key, stream in streams.items():
                if len(stream) < 3:
                    continue
                
                # A. DAG Longest Path
                stream.sort(key=lambda x: (x['p'], x['x']))
                n = len(stream)
                dp_lengths = [1] * n
                dp_prev = [-1] * n
                
                for i in range(1, n):
                    for j in range(i):
                        u = stream[j]
                        v = stream[i]
                        
                        dp_gap = v['p'] - u['p']
                        dv_gap = v['val'] - u['val']
                        
                        if dp_gap > 0 and dv_gap > 0:
                            offset_shift = abs(dp_gap - dv_gap)
                            if offset_shift <= 20: 
                                if dp_lengths[j] + 1 > dp_lengths[i]:
                                    dp_lengths[i] = dp_lengths[j] + 1
                                    dp_prev[i] = j
                                    
                max_idx = dp_lengths.index(max(dp_lengths))
                stream_max_chain = []
                curr = max_idx
                while curr != -1:
                    stream_max_chain.append(stream[curr])
                    curr = dp_prev[curr]
                stream_max_chain.reverse()
                
                if len(stream_max_chain) < 3:
                    continue

                # B. Pearson Correlation
                p_vals = [c['p'] for c in stream_max_chain]
                v_vals = [c['val'] for c in stream_max_chain]
                mean_p = sum(p_vals) / len(p_vals)
                mean_v = sum(v_vals) / len(v_vals)
                
                var_p = sum((p - mean_p)**2 for p in p_vals)
                var_v = sum((v - mean_v)**2 for v in v_vals)
                
                if var_p == 0 or var_v == 0:
                    continue 
                    
                cov = sum((p - mean_p) * (v - mean_v) for p, v in zip(p_vals, v_vals))
                r = cov / math.sqrt(var_p * var_v)
                slope = cov / var_p
                
                if r < 0.5 or slope < 0.2:
                    continue

                # C. Geometric Penalty
                even_x = [c['x'] for c in stream_max_chain if c['p'] % 2 == 0]
                odd_x = [c['x'] for c in stream_max_chain if c['p'] % 2 != 0]
                std_x_even = statistics.stdev(even_x) if len(even_x) > 1 else 0.0
                std_x_odd = statistics.stdev(odd_x) if len(odd_x) > 1 else 0.0
                avg_std_x = (std_x_even + std_x_odd) / 2.0
                
                score = (len(stream_max_chain) * r) / (avg_std_x + 1.0)
                
                if score > best_score:
                    best_score = score
                    target_stream_key = key
                    winning_chain = stream_max_chain

            if target_stream_key:
                target_type, target_y_label = target_stream_key
            else:
                target_type, target_y_label = None, None

            logger.info(
                'STREAM_SELECTED: type=%s zone=%s best_score=%.4f chain_len=%d',
                target_type, target_y_label, best_score, len(winning_chain)
            )
            
            page_map = []
            curr_seg = None
            winning_cands_by_page = {c['p']: c for c in winning_chain}
            
            for p in range(1, self.topo_scan_limit + 1):
                if p not in winning_cands_by_page:
                    continue
                
                best = winning_cands_by_page[p]
                val, n_type = best['val'], best['type']
                
                if curr_seg and n_type == curr_seg['numbering']:
                    if val > curr_seg['last']:
                        P1 = curr_seg['physical_end']
                        N1 = curr_seg['last']
                        P2 = p
                        N2 = val
                        
                        stride = curr_seg.get('stride')
                        if stride is None:
                            stride = 1

                        raw_ratio = (N2 - N1) / stride
                        if not raw_ratio.is_integer():
                            missing_printed = 0
                        else:
                            missing_printed = int(raw_ratio) - 1
                            if missing_printed < 0:
                                missing_printed = 0
                            
                        gap_physical_pages = P2 - P1 - 1
                        
                        if gap_physical_pages == 0 and missing_printed == 0:
                            if curr_seg['run'] == 1:
                                curr_seg['stride'] = val - curr_seg['last']
                            curr_seg['printed_end'] = N2
                            curr_seg['physical_end'] = P2
                            curr_seg['last'] = N2
                            curr_seg['run'] += 1
                            
                        elif gap_physical_pages > missing_printed:
                            assert body_size is not None and body_size > 0
                            gap_pages = []
                            for phys_p in range(P1 + 1, P2):
                                weight = self._compute_content_weight(phys_p - 1, body_size)
                                gap_pages.append({'phys_p': phys_p, 'weight': weight})
                            
                            gap_pages.sort(key=lambda x: x['weight'], reverse=True)
                            assigned_pages = gap_pages[:missing_printed]
                            spacer_pages = gap_pages[missing_printed:]
                            
                            current_printed = N1 + stride
                            for _ in assigned_pages:
                                current_printed += stride
                                
                            for page_data in spacer_pages:
                                curr_seg.setdefault('spacers', []).append(page_data['phys_p'])

                            curr_seg['printed_end'] = N2
                            curr_seg['physical_end'] = P2
                            curr_seg['last'] = N2
                            curr_seg['run'] += 1 + missing_printed

                        elif gap_physical_pages == missing_printed:
                            curr_seg['printed_end'] = N2
                            curr_seg['physical_end'] = P2
                            curr_seg['last'] = N2
                            curr_seg['run'] += 1 + missing_printed

                        elif gap_physical_pages < missing_printed:
                            if curr_seg['run'] < 3:
                                logger.warning("SHORT_SEGMENT_RETAINED: physical=%d-%d printed=%d-%d type=%s run=%d", 
                                            curr_seg['physical_start'], curr_seg['physical_end'], 
                                            curr_seg['printed_start'], curr_seg['printed_end'], 
                                            curr_seg['numbering'], curr_seg['run'])
                            page_map.append({
                                'physical_start': curr_seg['physical_start'],
                                'physical_end': curr_seg['physical_end'],
                                'printed_start': curr_seg['printed_start'],
                                'printed_end': curr_seg['printed_end'],
                                'numbering': curr_seg['numbering'],
                                'spacers': curr_seg.get('spacers', [])
                            })
                            curr_seg = {
                                'physical_start': P2, 'physical_end': P2, 'printed_start': N2, 'printed_end': N2, 
                                'last': N2, 'run': 1, 'numbering': n_type, 
                                'stride': None, 'spacers': []
                            }
                    else:
                        if curr_seg['run'] < 3:
                            logger.warning("SHORT_SEGMENT_RETAINED: physical=%d-%d printed=%d-%d type=%s run=%d", 
                                            curr_seg['physical_start'], curr_seg['physical_end'], 
                                            curr_seg['printed_start'], curr_seg['printed_end'], 
                                            curr_seg['numbering'], curr_seg['run'])
                        page_map.append({
                            'physical_start': curr_seg['physical_start'],
                            'physical_end': curr_seg['physical_end'],
                            'printed_start': curr_seg['printed_start'],
                            'printed_end': curr_seg['printed_end'],
                            'numbering': curr_seg['numbering'],
                            'spacers': curr_seg.get('spacers', [])
                        })
                        curr_seg = {
                            'physical_start': p, 'physical_end': p, 'printed_start': val, 'printed_end': val, 
                            'last': val, 'run': 1, 'numbering': n_type, 'stride': None, 'spacers': []
                        }

                else:
                    if curr_seg:
                        if curr_seg['run'] < 3:
                            logger.warning("SHORT_SEGMENT_RETAINED: physical=%d-%d printed=%d-%d type=%s run=%d", 
                                            curr_seg['physical_start'], curr_seg['physical_end'], 
                                            curr_seg['printed_start'], curr_seg['printed_end'], 
                                            curr_seg['numbering'], curr_seg['run'])
                        page_map.append({
                            'physical_start': curr_seg['physical_start'],
                            'physical_end': curr_seg['physical_end'],
                            'printed_start': curr_seg['printed_start'],
                            'printed_end': curr_seg['printed_end'],
                            'numbering': curr_seg['numbering'],
                            'spacers': curr_seg.get('spacers', [])
                        })
                        
                    curr_seg = {
                        'physical_start': p, 'physical_end': p, 'printed_start': val, 'printed_end': val, 
                        'last': val, 'run': 1, 'numbering': n_type, 'stride': None, 'spacers': []
                    }

            if curr_seg:
                if curr_seg['run'] < 3:
                    logger.warning("SHORT_SEGMENT_RETAINED: physical=%d-%d printed=%d-%d type=%s run=%d", 
                                    curr_seg['physical_start'], curr_seg['physical_end'], 
                                    curr_seg['printed_start'], curr_seg['printed_end'], 
                                    curr_seg['numbering'], curr_seg['run'])
                page_map.append({
                    'physical_start': curr_seg['physical_start'],
                    'physical_end': curr_seg['physical_end'],
                    'printed_start': curr_seg['printed_start'],
                    'printed_end': curr_seg['printed_end'],
                    'numbering': curr_seg['numbering'],
                    'spacers': curr_seg.get('spacers', [])
                })

            if not page_map:
                raise RuntimeError("CRITICAL: page_map is empty. TOPOLOGY_INDUCTION_FAILED.")

            # --- 5. ASSET DETECTION ---
            assets = []
            for m_type in ['Fig', 'Map', 'Table']:
                eligible = [idx for idx in clusters if idx != body_idx and clusters[idx]['coverage'] < 0.4 and clusters[idx]['avg_per_page'] < self.MAX_HEADER_AVG_PER_PAGE]
                if not eligible: continue
                
                best_asset_idx = max(eligible, key=lambda k: clusters[k]['markers'][m_type] / max(clusters[k]['coverage'], 0.01))
                c = clusters[best_asset_idx]
                
                if c['markers'][m_type] <= 2: continue
                
                markers_by_page = defaultdict(int)
                for o in slots[best_asset_idx]:
                    if re.search(rf'\b{m_type}\b', o['text'], re.I):
                        markers_by_page[o['page']] += 1
                
                valid_segment_found = False
                for seg in page_map:
                    seg_start, seg_end = seg['physical_start'], seg['physical_end']
                    seg_length = (seg_end - seg_start) + 1
                    seg_markers = sum(markers_by_page[p] for p in range(seg_start, seg_end + 1))
                    
                    if seg_markers == 0: continue
                    
                    seg_density = seg_markers / seg_length
                    if seg_density > self.MAX_ASSET_MARKERS_PER_PAGE:
                        pass # Ignore overly dense noisy clusters
                    else: 
                        valid_segment_found = True
                        
                if valid_segment_found:
                    assets.append({'asset_type': m_type.lower(), 'visual_signature': {'font_size': {'min': round(c['center']-0.3, 2), 'max': round(c['center']+0.3, 2)}}})

            # --- 6. HIERARCHY ASSEMBLY ---
            # Identifies headings by finding fonts distinctly larger than the body text
            headers = sorted([idx for idx in clusters if clusters[idx]['center'] > body_size * 1.1 and clusters[idx]['avg_per_page'] <= self.MAX_HEADER_AVG_PER_PAGE], 
                            key=lambda k: (clusters[k]['center'], clusters[k]['bold_ratio']), reverse=True)
            
            hierarchy = []
            for i, idx in enumerate(headers):
                c = clusters[idx]
                spread = max(0.2, min(c['center'] * 0.03, 0.8))
                min_v, max_v = c['center'] - spread, c['center'] + spread
                if i > 0: min_v = max(min_v, (c['center'] + clusters[headers[i-1]]['center'])/2)
                if i < len(headers)-1: max_v = min(max_v, (c['center'] + clusters[headers[i+1]]['center'])/2)
                if min_v >= max_v: min_v, max_v = c['center'] - 0.1, c['center'] + 0.1

                _primary_label = (struct_vocab.get('primary_marker') or 'chapter').strip().lower()
                _secondary_label = 'subtopic' # TODO: Sprint 2 — replace with AI-derived role labels from layout_templates schema.
                _level_label = _primary_label if i == 0 else f'{_secondary_label}_{i}'

                hierarchy.append({
                    'level_rank': i + 1, 
                    'has_explicit_marker': True, 
                    'numbering_style': 'none', 
                    'has_named_title': True,
                    # Provide a baseline semantic label for indexer URNs
                    'label_hypothesis': {'preferred_label': _level_label, 'confidence': struct_vocab.get('confidence', 0.0)},
                    'visual_signature': {'font_size': {'min': round(min_v, 2), 'max': round(max_v, 2)}, 'is_bold': c['bold_ratio'] > 0.5}
                })
                
            

            confidence = round(sum((s['physical_end'] - s['physical_start'] + 1) for s in page_map) / self.topo_scan_limit, 2)
            
            return {
                'profiling_diagnostics': {'profiling_status': 'success', 'page_map_confidence': confidence},
                'page_map': page_map, 
                'hierarchy_levels': hierarchy, 
                'assets': assets,
                'structural_vocabulary': struct_vocab if struct_vocab.get('primary_marker') else {}
            }
        finally:
            self.doc.close()

def auto_profile_with_gemini(pdf_path, config_path, api_key=None, doc_name="unknown", mode="full", vocab_override=None, app_settings=None):
    profiler = EnterpriseProfiler(pdf_path, api_key=api_key, model_name="gemini-2.0-flash", doc_name=doc_name, mode=mode, vocab_override=vocab_override, app_settings=app_settings)
    config = profiler.run()
    with open(config_path, 'w') as f:
        yaml.dump(config, f, sort_keys=False)