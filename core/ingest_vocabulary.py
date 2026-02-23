import argparse
import json
import os
import sys
import fitz
import statistics
from datetime import datetime

# Ensure core modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.vocabulary_registry import VocabularyRegistry

def extract_top_cluster_text(pdf_path: str) -> list[str]:
    """
    Simplified cluster extraction logic mirroring EnterpriseProfiler.
    Returns a list of text strings from the largest font clusters.
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    scan_limit = min(100, total_pages)
    
    # 1. Calculate Grid
    samples = []
    sample_pages = [int(i * (total_pages - 1) / 9) for i in range(min(10, total_pages))]
    for p in sample_pages:
        for b in doc[p].get_text("dict").get("blocks", []):
            if b['type'] == 0:
                for line in b["lines"]:
                    for span in line["spans"]:
                        samples.append(span["size"])
    
    unique_sorted = sorted(list(set(samples)))
    deltas = [unique_sorted[i+1] - unique_sorted[i] for i in range(len(unique_sorted)-1) if unique_sorted[i+1] - unique_sorted[i] > 0.05]
    grid_size = max(0.1, min(0.25, statistics.median(deltas) if deltas else 0.1))

    # 2. Collect Slots
    from collections import defaultdict
    slots = defaultdict(list)
    
    for p_idx in range(scan_limit):
        page = doc[p_idx]
        for b in page.get_text("dict").get("blocks", []):
            if b['type'] != 0: continue
            for line in b["lines"]:
                chars = " ".join(s["text"].strip() for s in line["spans"] if s["text"].strip()).strip()
                if not chars: continue
                primary_span = max(line["spans"], key=lambda s: (s["bbox"][2] - s["bbox"][0]) * s["size"])
                raw_size = primary_span["size"]
                grid_idx = int(raw_size // grid_size)
                
                # Simplified slot object
                slots[grid_idx].append({
                    'size': raw_size,
                    'chars': len(chars),
                    'text': chars,
                    'page': p_idx
                })

    if not slots:
        doc.close()
        return []

    # 3. Cluster Stats
    clusters = {}
    for idx, obs in slots.items():
        center = statistics.median([o['size'] for o in obs])
        pages = set(o['page'] for o in obs)
        clusters[idx] = {
            'center': center,
            'coverage': len(pages) / scan_limit,
            'density': sum(o['chars'] for o in obs), # Simplified density
            'samples': [o['text'] for o in obs]
        }

    # 4. Identify Body and Top Clusters
    # Simplified body selection: max coverage * density
    body_idx = max(clusters.keys(), key=lambda k: clusters[k]['coverage'] * clusters[k]['density'])
    body_size = clusters[body_idx]['center']

    top_cluster_text = []
    for idx, c in clusters.items():
        if c['center'] > body_size * 1.5:
            top_cluster_text.extend(c['samples'])
            
    doc.close()
    return top_cluster_text

def main():
    parser = argparse.ArgumentParser(description="Vocabulary Registry Management Tool")
    parser.add_argument("--doc", help="Document name (identifier)")
    parser.add_argument("--file", help="Path to JSON response file for ingestion")
    parser.add_argument("--list", action="store_true", help="List all documents in registry")
    parser.add_argument("--clear", action="store_true", help="Invalidate an entry")
    parser.add_argument("--source", choices=['manual_ingest', 'gemini_api'], help="Source to clear")
    parser.add_argument("--validate", action="store_true", help="Run validation against PDF")
    parser.add_argument("--pdf", help="Path to PDF for validation")

    args = parser.parse_args()
    registry = VocabularyRegistry()

    if args.list:
        print(f"{'DOC NAME':<30} | {'SOURCE':<15} | {'MARKER':<15} | {'TIMESTAMP':<25} | {'STATUS'}")
        print("-" * 100)
        for entry in registry.list_all():
            status = "INVALID" if entry.get('invalidated') else "ACTIVE"
            print(f"{entry['doc_name']:<30} | {entry['source']:<15} | {entry.get('primary_marker', 'N/A'):<15} | {entry['timestamp']:<25} | {status}")
        return

    if args.clear:
        if not args.doc or not args.source:
            print("Error: --clear requires --doc and --source")
            return
        registry.clear(args.doc, args.source)
        print(f"Cleared latest entry for {args.doc} from {args.source}")
        return

    # Validation Logic (Runs if explicit --validate OR if ingesting with --file and --pdf present)
    if args.validate or (args.doc and args.pdf and not args.file):
        if not args.doc or not args.pdf:
            print("Error: Validation requires --doc and --pdf")
            return
        
        print(f"Extracting cluster text from {args.pdf}...")
        samples = extract_top_cluster_text(args.pdf)
        print(f"Extracted {len(samples)} text samples from top clusters.")
        
        def validator(entry):
            m = entry.get('primary_marker')
            if not m: return False
            return any(m.lower() in s.lower() for s in samples)

        print(f"Validating registry entries for {args.doc}...")
        hit = registry.get(args.doc, validator, top_cluster_samples=samples)
        if hit and hit['source'] in ['manual_ingest', 'gemini_api']:
            print(f"PASS: Found valid entry from {hit['source']} (Marker: {hit['primary_marker']})")
        else:
            print(f"FAIL: No valid entries found. Fallback: {hit['source']} ({hit['primary_marker']})")
        return

    if args.file:
        if not args.doc:
            print("Error: Ingestion requires --doc")
            return
        
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.")
            return
            
        with open(args.file, 'r') as f:
            data = json.load(f)
            
        required = ['primary_marker', 'chapter_count', 'compound_titles', 'font_role_map']
        if not all(k in data for k in required):
            print(f"Error: JSON missing required fields: {required}")
            return
            
        registry.write_manual_result(args.doc, data)
        print(f"Successfully ingested manual result for {args.doc} at {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()