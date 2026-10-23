"""Node Identity Strategy module.

Separates stable cross-version logical identity from version-specific node instances.
"""
import re
import unicodedata
from typing import Optional

def slugify(text: str) -> str:
    """Create a URL-safe, normalized slug from text."""
    if not text:
        return "root"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", text)[:50]

class NodeIdentityManager:
    """Manages logical IDs and version-scoped node IDs."""

    @staticmethod
    def generate_logical_id(section_number: Optional[str], title: str, parent_logical_id: Optional[str] = None) -> str:
        """
        Generate a stable logical ID across document versions.
        Format: sec:<number>:<slug_title> or sec:sub:<slug_title> under parent.
        """
        title_slug = slugify(title)
        
        if section_number:
            num_clean = section_number.strip().rstrip(".")
            return f"sec:{num_clean}:{title_slug}"
        elif parent_logical_id:
            return f"{parent_logical_id}:sub:{title_slug}"
        else:
            return f"sec:root:{title_slug}"

    @staticmethod
    def generate_node_id(document_version: str, logical_id: str) -> str:
        """
        Generate a unique, version-pinned node ID.
        E.g.: 'v1_sec_2_1_general-specifications'
        """
        clean_logical = logical_id.replace(":", "_").replace(".", "_")
        return f"{document_version}_{clean_logical}"
