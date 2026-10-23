"""Deterministic content hashing module."""
import hashlib
import json
import unicodedata
from typing import List, Dict, Any, Optional

class ContentHasher:
    """Computes deterministic SHA-256 hashes of section titles, body texts, and tables."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize Unicode characters, replace ligatures, and collapse extra whitespace."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKD", text)
        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        return "\n".join(lines)

    @classmethod
    def hash_node_content(
        cls,
        title: str,
        section_number: Optional[str],
        full_text: str,
        tables: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Produce a deterministic SHA-256 hash.
        Includes normalized title, section number, body text, and canonical table structure.
        """
        hasher = hashlib.sha256()
        
        norm_title = cls.normalize_text(title)
        norm_num = (section_number or "").strip()
        norm_body = cls.normalize_text(full_text)
        
        hasher.update(norm_num.encode("utf-8"))
        hasher.update(b"\n---TITLE---\n")
        hasher.update(norm_title.encode("utf-8"))
        hasher.update(b"\n---BODY---\n")
        hasher.update(norm_body.encode("utf-8"))
        
        if tables:
            hasher.update(b"\n---TABLES---\n")
            # Canonical representation of tables (ignoring page/bbox, preserving rows)
            clean_tables = []
            for t in tables:
                clean_tables.append({
                    "headers": [cls.normalize_text(h) for h in t.get("headers", [])],
                    "rows": [
                        [cls.normalize_text(c) for c in row]
                        for row in t.get("rows", [])
                    ]
                })
            canonical_json = json.dumps(clean_tables, sort_keys=True, ensure_ascii=True)
            hasher.update(canonical_json.encode("utf-8"))
            
        return hasher.hexdigest()
