import os
import fitz
import logging
import argparse
import glob
import yaml
from dotenv import load_dotenv

from core.profiler import auto_profile_with_gemini
from core.indexer import EnterpriseIndexer
from core.miner import EnterpriseMiner
from core.resolver import EnterpriseResolver
from core.annotator import EnterpriseAnnotator

load_dotenv()

class PDFAccessibilityEngine:
    """
    Orchestrates the 5-phase compilation of a static PDF into a
    semantically hyperlinked and reference-linked resource.
    """

    def __init__(self, api_key: str, debug: bool = False, allow_partial: bool = False, reprofile: bool = False, mode: str = "full", vocab_override: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("CRITICAL_CONFIG: Valid Gemini API Key is required.")
        
        self.api_key = api_key.strip()
        self.debug = debug
        self.allow_partial = allow_partial
        self.reprofile = reprofile
        self.mode = mode
        self.vocab_override = vocab_override
        self.root = os.path.dirname(os.path.abspath(__file__))
        
        # Establishing isolated paths
        self.input_dir = os.path.join(self.root, "input")
        self.output_dir = os.path.join(self.root, "output")
        self.config_dir = os.path.join(self.root, "config")
        self.log_dir = os.path.join(self.root, "logs") # New logs directory
        
        self._provision_infrastructure()
        
        # Load global app settings
        settings_path = os.path.join(self.config_dir, 'app_settings.yaml')
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                self.app_settings = yaml.safe_load(f) or {}
        else:
            self.app_settings = {}

    def _provision_infrastructure(self):
        """Ensures the full directory lifecycle exists at runtime."""
        for folder in [self.input_dir, self.output_dir, self.config_dir, self.log_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    def _log_phase0_debug(self, config_path: str):
        """Elaborate diagnostic logging for Phase 0 artifacts."""
        logger = logging.getLogger("PipelineOrchestrator")
        logger.debug("--- DEBUG: PHASE 0 (PROFILER) ARTIFACTS ---")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            page_map = config.get("page_map", [])
            logger.debug("Page Map Segments (%d total):", len(page_map))
            for i, seg in enumerate(page_map):
                logger.debug("  [%d] Type: %-6s | Physical: %3d-%-3d | Printed: %3d-%-3d", 
                             i, seg.get('numbering'), seg.get('physical_start'), seg.get('physical_end'),
                             seg.get('printed_start'), seg.get('printed_end'))
                
            hierarchy = config.get("hierarchy_levels", [])
            logger.debug("Hierarchy Levels Identified (%d total):", len(hierarchy))
            for i, lvl in enumerate(hierarchy):
                font_sig = lvl.get('visual_signature', {}).get('font_size', {})
                logger.debug("  [%d] Level %d | Label: '%s' | Size: [%.2f - %.2f]", 
                             i, lvl.get('level_rank'), lvl.get('label_hypothesis', {}).get('preferred_label'),
                             font_sig.get('min', 0), font_sig.get('max', 0))

        except Exception as e:
            logger.debug("Failed to read config for debug logging: %s", str(e))

    def _log_phase1_debug(self, ast: list):
        """Elaborate diagnostic logging for Phase 1 AST nodes."""
        logger = logging.getLogger("PipelineOrchestrator")
        logger.debug("--- DEBUG: PHASE 1 (INDEXER) AST NODES ---")
        logger.debug("Total TargetNodes Extracted: %d", len(ast))
        for i, node in enumerate(ast):
            logger.debug("  Node %03d | ID: %-15s | Type: %-10s | Page: %-3d | Text: '%s'", 
                         i+1, node.target_id, node.target_type, node.page_number, node.exact_name)

    def process_document(self, pdf_path: str):
        logger = logging.getLogger("PipelineOrchestrator")
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        config_path = os.path.join(self.config_dir, f"{base_name}_rulebook.yaml")
        output_pdf = os.path.join(self.output_dir, f"AI_LINKED_{base_name}.pdf")

        logger.info("--- COMPILING DOCUMENT: %s ---", base_name)

        try:
            # PHASE 0: PROFILER
            if os.path.exists(config_path) and not self.reprofile:
                logger.info("PHASE0_CACHED: Rulebook exists, skipping profiling.")
            else:
                if self.reprofile and os.path.exists(config_path):
                    os.remove(config_path)
                auto_profile_with_gemini(pdf_path, config_path, self.api_key, base_name, mode=self.mode, vocab_override=self.vocab_override, app_settings=self.app_settings)
                if self.debug: self._log_phase0_debug(config_path)
            
            # PHASE 1: INDEXER
            indexer = EnterpriseIndexer(pdf_path, config_path)
            ast = indexer.build_ast()
            if self.debug: self._log_phase1_debug(ast)
            
            # PHASE 2: MINER (The Safeguard)
            miner = EnterpriseMiner()
            refs = []
            
            doc = fitz.open(pdf_path)
            try:
                for page_idx, page in enumerate(doc):
                    blocks = page.get_text("dict").get("blocks", [])
                    for b in blocks:
                        if b['type'] != 0:
                            continue
                        
                        block_text = " ".join(["".join([s["text"] for s in line["spans"]]) for line in b["lines"]]).strip()
                        if not block_text:
                            continue
                        
                        refs.extend(miner.mine_page_references(page_idx, page, block_text, b['bbox']))
            finally:
                doc.close()
            
            logger.info("Phase 2 Miner complete. Extracted %d references.", len(refs))
            
            # PHASE 3: RESOLVER
            resolver = EnterpriseResolver(ast, refs, config_path)
            resolved_refs = resolver.resolve()
            
            # PHASE 4: ANNOTATOR
            min_conf = self.app_settings.get('pipeline_tuning', {}).get('min_link_confidence', 0.75)
            annotator = EnterpriseAnnotator(pdf_path, output_pdf, debug_mode=self.debug, min_confidence=min_conf)
            annotator.annotate(resolved_refs)
            
            logger.info("PIPELINE_SUCCESS: %s", output_pdf)

        except Exception as e:
            logger.error("PIPELINE_FAULT: Failed on %s. Error: %s. No output written.", base_name, str(e))
            raise

    def run_batch(self):
        logger = logging.getLogger("PipelineOrchestrator")
        queue = sorted(glob.glob(os.path.join(self.input_dir, "*.pdf")))
        
        if not queue:
            logger.warning("Queue empty. Place PDFs in /input to begin.")
            return

        logger.info("BATCH_INITIALIZED: Processing %d documents.", len(queue))
        success_count, failure_count = 0, 0
        
        for i, pdf_path in enumerate(queue):
            logger.info("ORCHESTRATION_PROGRESS: [%d/%d]", i + 1, len(queue))
            try:
                self.process_document(pdf_path)
                success_count += 1
            except Exception:
                failure_count += 1
                continue
            
        logger.info("BATCH_COMPLETE: %d succeeded, %d failed.", success_count, failure_count)

def setup_enterprise_logging(debug_mode: bool):
    """Configures dual-channel logging (Console + File)."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 1. Console Handler (Terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # 2. File Handler (Persistent Log)
    # Ensure logs directory exists before creating the file
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)
    file_handler = logging.FileHandler(os.path.join("logs", "pipeline_execution.log"), mode='w', encoding='utf-8')
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

if __name__ == "__main__":
    raw_env_key = os.getenv("GEMINI_API_KEY")
    env_key = raw_env_key.strip() if raw_env_key else None

    parser = argparse.ArgumentParser(description="PDF Accessibility and Link Enhancement Engine")
    parser.add_argument("--key", default=env_key, help="Gemini API key. Overrides the GEMINI_API_KEY value in .env")
    parser.add_argument("--debug", action="store_true", help="Enable verbose diagnostic logging including all AST nodes and phase artifacts")
    parser.add_argument("--allow-partial", action="store_true", help="Continue pipeline even if a phase produces incomplete results. Use for testing only")
    parser.add_argument("--reprofile", action="store_true", help="Delete and regenerate the rulebook YAML for all documents in the batch, forcing a fresh Phase 0 including a new Gemini vocabulary call")
    parser.add_argument("--list-pending", action="store_true", help="Print all documents awaiting manual vocabulary review and exit")
    parser.add_argument("--mode", choices=['full', 'no-api', 'offline', 'manual-only', 'override'], default='full', help="Vocabulary resolution mode. full=all sources enabled. no-api=skip API call. offline=no API and no packet generation. manual-only=halt document if no registry or manual file found. override=requires --vocab flag, skips all resolution.")
    parser.add_argument("--vocab", help="Runtime vocabulary override (e.g. 'Theme'). Used with --mode override or as a quick single-run label. Not stored in registry.")
    
    args = parser.parse_args()
    
    # Initialize our dual-channel logging system
    setup_enterprise_logging(args.debug)
    logger = logging.getLogger("Main")
    
    final_key = args.key.strip() if args.key else None

    if args.list_pending:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        manual_dir = os.path.join(root_dir, "config", "manual_review")
        pending = sorted(glob.glob(os.path.join(manual_dir, "*_pending.flag")))
        print(f"{'DOC NAME':<40} | {'TIMESTAMP'}")
        print("-" * 65)
        for p in pending:
            name = os.path.basename(p).replace("_pending.flag", "")
            with open(p, 'r') as f:
                lines = f.readlines()
                ts = lines[1].strip() if len(lines) > 1 else "N/A"
            print(f"{name:<40} | {ts}")
        exit(0)
    
    if not final_key:
        logger.error("CRITICAL: No Gemini API Key found. Check your .env file or --key flag.")
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        manual_dir = os.path.join(root_dir, "config", "manual_review")
        pending_count = len(glob.glob(os.path.join(manual_dir, "*_pending.flag")))
        batch_count = len(glob.glob(os.path.join(manual_dir, "batch_*_prompt.txt")))
        
        pending_msg = ""
        if pending_count > 0:
            pending_msg = f"\n  Pending review: {pending_count} documents | Batches: {batch_count} | See config/manual_review/"

        logger.info("Starting PDF Accessibility and Link Enhancement Engine\n"
                    "  Mode          : %s\n"
                    "  Debug         : %s\n"
                    "  Allow-partial : %s\n"
                    "  Reprofile     : %s\n"
                    "  Vocab override: %s\n"
                    "  API key       : present\n"
                    "  Input dir     : %s\n"
                    "  Output dir    : %s\n"
                    "  Config dir    : %s%s",
                    args.mode,
                    "ON" if args.debug else "OFF", 
                    "ON" if args.allow_partial else "OFF", 
                    "ON" if args.reprofile else "OFF",
                    args.vocab if args.vocab else 'none',
                    os.path.join(root_dir, "input"), 
                    os.path.join(root_dir, "output"), 
                    os.path.join(root_dir, "config"),
                    pending_msg)
        
        engine = PDFAccessibilityEngine(final_key, debug=args.debug, allow_partial=args.allow_partial, reprofile=args.reprofile, mode=args.mode, vocab_override=args.vocab)
        engine.run_batch()

