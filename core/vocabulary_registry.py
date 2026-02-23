import os
import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)

KNOWN_STRUCTURAL_MARKERS = frozenset({
    'Chapter', 'Theme', 'Unit', 'Part', 'Lesson', 'Module', 'Section',
    'Volume', 'Topic', 'Book', 'Reading', 'Entry', 'Case', 'Story',
    'Week', 'Session', 'Block', 'Strand', 'Article', 'Clause', 'Rule',
    'Act', 'Schedule', 'Protocol', 'Trial', 'Experiment', 'Canto',
    'Tale', 'Verse', 'Epoch', 'Era', 'Period', 'Paath'
})

class VocabularyRegistry:
    """
    Manages persistent storage for structural vocabulary extracted from documents.
    Arbitrates between manual overrides and API-generated results.
    """

    def __init__(self):
        # Determine root relative to this file (core/vocabulary_registry.py -> root)
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.registry_dir = os.path.join(self.root, "config", "vocabulary_registry")
        
        if not os.path.exists(self.registry_dir):
            os.makedirs(self.registry_dir)
            
        self.api_store_path = os.path.join(self.registry_dir, "api_store.json")
        self.manual_store_path = os.path.join(self.registry_dir, "manual_store.json")
        self.validation_log_path = os.path.join(self.registry_dir, "validation_log.json")
        
        self._ensure_files()

    def _ensure_files(self):
        for path in [self.api_store_path, self.manual_store_path, self.validation_log_path]:
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump([], f)

    def _load_store(self, path: str) -> List[Dict]:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def _append_to_store(self, path: str, entry: Dict):
        data = self._load_store(path)
        data.append(entry)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def get(self, doc_name: str, validator_fn: Callable[[Dict], bool], top_cluster_samples: Optional[List[str]] = None) -> Dict:
        """
        Retrieves the most relevant vocabulary entry for a document.
        Priority: Manual Store (Latest Valid) -> API Store (Latest Valid).
        """
        manual_data = self._load_store(self.manual_store_path)
        api_data = self._load_store(self.api_store_path)
        
        # Sort by timestamp descending
        candidates = []
        candidates.extend([d for d in manual_data if d.get('doc_name') == doc_name])
        candidates.extend([d for d in api_data if d.get('doc_name') == doc_name])
        
        # Prioritize manual over api, but within same source, prioritize time.
        # Actually, the requirement is "manual store first, then api store".
        # So we process manual list first, then api list.
        
        sources_to_check = [
            ('manual_ingest', sorted([d for d in manual_data if d.get('doc_name') == doc_name], key=lambda x: x['timestamp'], reverse=True)),
            ('gemini_api', sorted([d for d in api_data if d.get('doc_name') == doc_name], key=lambda x: x['timestamp'], reverse=True))
        ]

        for source_name, entries in sources_to_check:
            for entry in entries:
                if entry.get('invalidated'):
                    continue
                
                is_valid = validator_fn(entry)
                
                # Log validation attempt
                log_entry = {
                    "source": source_name,
                    "doc_name": doc_name,
                    "timestamp": datetime.now().isoformat(),
                    "result": "pass" if is_valid else "fail"
                }
                self._append_to_store(self.validation_log_path, log_entry)
                
                if is_valid:
                    return entry
        
        # Fallback Logic
        fallback_entry = None
        
        if top_cluster_samples:
            first_words = []
            for s in top_cluster_samples:
                # Extract first alpha sequence
                match = re.match(r'^\s*([a-zA-Z]+)', s)
                if match:
                    first_words.append(match.group(1).title())
            
            if first_words:
                common = Counter(first_words).most_common(1)
                if common:
                    token, _ = common[0]
                    if token.title() in KNOWN_STRUCTURAL_MARKERS:
                        fallback_entry = {
                            "primary_marker": token,
                            "source": "statistical_fallback",
                            "confidence": 0.5,
                            "doc_name": doc_name,
                            "timestamp": datetime.now().isoformat()
                        }

        if not fallback_entry:
            fallback_entry = {
                "primary_marker": "Chapter",
                "source": "default_fallback",
                "confidence": 0.1,
                "doc_name": doc_name,
                "timestamp": datetime.now().isoformat()
            }
            
        log_entry = {
            "source": fallback_entry['source'],
            "doc_name": doc_name,
            "timestamp": datetime.now().isoformat(),
            "result": "fallback_generated"
        }
        self._append_to_store(self.validation_log_path, log_entry)
        
        return fallback_entry

    def write_api_result(self, doc_name: str, data: Dict):
        entry = {**data, "doc_name": doc_name, "source": "gemini_api", "timestamp": datetime.now().isoformat(), "invalidated": False}
        self._append_to_store(self.api_store_path, entry)

    def write_manual_result(self, doc_name: str, data: Dict):
        entry = {**data, "doc_name": doc_name, "source": "manual_ingest", "timestamp": datetime.now().isoformat(), "invalidated": False}
        self._append_to_store(self.manual_store_path, entry)

    def list_all(self) -> List[Dict]:
        manual = self._load_store(self.manual_store_path)
        api = self._load_store(self.api_store_path)
        combined = {}
        
        # Aggregate latest per doc
        for entry in manual + api:
            doc = entry['doc_name']
            if doc not in combined or entry['timestamp'] > combined[doc]['timestamp']:
                combined[doc] = entry
        return list(combined.values())

    def clear(self, doc_name: str, source: str):
        path = self.manual_store_path if source == 'manual_ingest' else self.api_store_path
        data = self._load_store(path)
        # Invalidate latest matching
        matches = [i for i, d in enumerate(data) if d['doc_name'] == doc_name and not d.get('invalidated')]
        if matches:
            # Invalidate the most recent one
            idx = matches[-1] 
            data[idx]['invalidated'] = True
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)