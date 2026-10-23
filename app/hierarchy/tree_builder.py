"""Hierarchy tree builder and parent-child relationship resolver."""
import json
from typing import List, Dict, Any, Optional

from app.ingestion.pdf_extractor import RawSectionBlock
from app.hierarchy.identity import NodeIdentityManager
from app.hierarchy.hasher import ContentHasher
from app.core.logging import logger

class NormalizedNodeData:
    def __init__(
        self,
        node_id: str,
        document_version: str,
        logical_id: str,
        parent_id: Optional[str],
        title: str,
        section_number: Optional[str],
        full_text: str,
        node_type: str,
        page_start: int,
        page_end: int,
        bbox: List[float],
        tables: List[Dict[str, Any]],
        content_hash: str,
        warnings: List[str],
        order_index: int
    ):
        self.node_id = node_id
        self.document_version = document_version
        self.logical_id = logical_id
        self.parent_id = parent_id
        self.title = title
        self.section_number = section_number
        self.full_text = full_text
        self.node_type = node_type
        self.page_start = page_start
        self.page_end = page_end
        self.bbox = bbox
        self.tables = tables
        self.content_hash = content_hash
        self.warnings = warnings
        self.order_index = order_index
        self.children: List["NormalizedNodeData"] = []

class HierarchyTreeBuilder:
    """Builds a normalized, parent-linked tree of section nodes."""

    @staticmethod
    def _find_parent_for_section(
        num: Optional[str],
        active_nodes: List[NormalizedNodeData]
    ) -> Optional[NormalizedNodeData]:
        """
        Find closest ancestor for a section based on dot-separated numbering.
        Handles missing intermediate numbers by traversing upwards.
        """
        if not num or "." not in num:
            return None  # Top-level section

        parts = num.split(".")
        # Try progressively shorter prefixes (e.g. for 2.1.1.1, try 2.1.1, then 2.1, then 2)
        for i in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:i])
            for node in reversed(active_nodes):
                if node.section_number == prefix:
                    return node
        return None

    @classmethod
    def build_hierarchy(
        cls,
        raw_sections: List[RawSectionBlock],
        document_version: str
    ) -> List[NormalizedNodeData]:
        """Convert raw section blocks into normalized, parent-linked nodes."""
        normalized_nodes: List[NormalizedNodeData] = []
        node_by_id: Dict[str, NormalizedNodeData] = {}

        for idx, raw in enumerate(raw_sections):
            logical_id = NodeIdentityManager.generate_logical_id(raw.section_number, raw.title)
            node_id = NodeIdentityManager.generate_node_id(document_version, logical_id)
            
            # Avoid collision if duplicate headings exist in raw
            if node_id in node_by_id:
                node_id = f"{node_id}_{idx}"
                logical_id = f"{logical_id}_{idx}"

            # Determine parent
            parent_node = cls._find_parent_for_section(raw.section_number, normalized_nodes)
            parent_id = parent_node.node_id if parent_node else None

            # Node type
            if raw.level == 0:
                node_type = "document"
            elif raw.level == 1:
                node_type = "section"
            else:
                node_type = "subsection"

            full_text = raw.get_full_text()
            content_hash = ContentHasher.hash_node_content(
                title=raw.title,
                section_number=raw.section_number,
                full_text=full_text,
                tables=raw.tables
            )

            node_data = NormalizedNodeData(
                node_id=node_id,
                document_version=document_version,
                logical_id=logical_id,
                parent_id=parent_id,
                title=raw.title,
                section_number=raw.section_number,
                full_text=full_text,
                node_type=node_type,
                page_start=raw.page_start,
                page_end=raw.page_end,
                bbox=raw.bbox,
                tables=raw.tables,
                content_hash=content_hash,
                warnings=list(raw.warnings),
                order_index=idx
            )

            if parent_node:
                parent_node.children.append(node_data)

            normalized_nodes.append(node_data)
            node_by_id[node_id] = node_data

        return normalized_nodes
