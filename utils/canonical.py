"""
Option A: CENTRALIZED AUTHORITY.
This module is the single URN generation authority for the entire pipeline. 
Phases 1, 2, and 3 must import CanonicalURN to ensure grammatical consistency.
"""
import re

class CanonicalURN:
    """
    Centralized authority for URN generation and parsing.
    Enforces the naming contract across the pipeline to prevent URN mismatch.
    """

    @staticmethod
    def generate_page_urn(val: int, numbering_type: str = "arabic") -> str:
        """
        Generates a standardized page URN.
        Invariant Protected: Domain-Specific Namespace — Ensures all page references follow 
        the 'page:<type>:<val>' schema for Phase 3 routing.
        """
        return f"page:{numbering_type.lower()}:{val}"

    @staticmethod
    def generate_structural_urn(namespace: str, counter: int) -> str:
        """
        Generates a standardized structural asset or hierarchy URN.
        Invariant Protected: Zero-Padding Contract — Guarantees target_ids remain 
        lexicographically sortable and non-empty.
        """
        return f"{namespace.lower()}:{counter:02d}"

    @staticmethod
    def slugify(text: str, fallback: str = "theme") -> str:
        """
        Converts raw display text into a URL-safe namespace slug.
        Invariant Protected: URN Integrity — Strips non-alphanumeric artifacts that 
        would otherwise break regex validation in schemas.py.
        """
        text = text.lower().strip()
        slug = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
        return slug if slug else fallback

    @staticmethod
    def parse_page_urn(urn: str):
        """
        Deconstructs a page URN into its constituent parts.
        """
        # Invariant Protected: Namespace Filtering — Safely returns None for non-page URNs
        if not urn.startswith("page:"):
            return None, None
        
        parts = urn.split(":")
        # Invariant Protected: Fail-Fast Validation — Raises ValueError on malformed structures
        if len(parts) != 3:
            raise ValueError(f"MALFORMED_URN: Expected 3 parts in URN '{urn}', found {len(parts)}.")
        
        try:
            return parts[1], int(parts[2])
        except ValueError:
            raise ValueError(f"MALFORMED_URN: Non-integer page value in URN '{urn}'.")