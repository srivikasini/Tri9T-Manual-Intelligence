"""Change detection and classification between document versions."""
from typing import List, Dict, Any, Optional
from collections import Counter

from app.schemas.diff import ChangeType, NodeComparison, VersionComparisonResponse
from app.diffing.matcher import CrossVersionMatcher, NodeMatchResult
from app.diffing.differ import TextDiffer

class ChangeDetector:
    """Analyzes matched nodes and classifies changes into UNCHANGED, MODIFIED, MOVED, ADDED, REMOVED."""

    @classmethod
    def compare_versions(
        cls,
        base_version: str,
        target_version: str,
        base_nodes: List[Any],
        target_nodes: List[Any]
    ) -> VersionComparisonResponse:
        """Compare all nodes between base and target versions."""
        matches: List[NodeMatchResult] = CrossVersionMatcher.match_nodes(base_nodes, target_nodes)
        
        comparisons: List[NodeComparison] = []
        counts: Counter = Counter()

        base_parent_map = {n.id: n.logical_id for n in base_nodes}
        target_parent_map = {n.id: n.logical_id for n in target_nodes}

        for m in matches:
            b = m.base_node
            t = m.target_node

            if b is not None and t is not None:
                b_parent_logical = base_parent_map.get(b.parent_id) if b.parent_id else None
                t_parent_logical = target_parent_map.get(t.parent_id) if t.parent_id else None
                is_moved = (b.section_number != t.section_number) or (b_parent_logical != t_parent_logical)

                # Both present: check if unchanged, modified, or moved
                if b.content_hash == t.content_hash:
                    # Check if moved
                    if is_moved:
                        chg_type = ChangeType.MOVED
                        explanation = f"Section moved from {b.section_number} to {t.section_number} with identical content"
                    else:
                        chg_type = ChangeType.UNCHANGED
                        explanation = "Content and structural position are identical"
                    
                    diff_str = None
                    diff_summary = None
                else:
                    # Hashes differ: MODIFIED (or MOVED & MODIFIED)
                    if is_moved:
                        chg_type = ChangeType.MOVED
                        explanation = f"Section moved from {b.section_number} to {t.section_number} and content modified"
                    else:
                        chg_type = ChangeType.MODIFIED
                        explanation = "Section content has changed"

                    diff_str, diff_summary = TextDiffer.generate_unified_diff(
                        b.full_text,
                        t.full_text,
                        from_label=f"{base_version}:{b.section_number}",
                        to_label=f"{target_version}:{t.section_number}"
                    )

                comp = NodeComparison(
                    logical_id=b.logical_id,
                    change_type=chg_type,
                    matching_confidence=m.confidence,
                    is_ambiguous=m.is_ambiguous,
                    base_node_id=b.id,
                    base_title=b.title,
                    base_section_number=b.section_number,
                    base_hash=b.content_hash,
                    base_parent_id=b.parent_id,
                    target_node_id=t.id,
                    target_title=t.title,
                    target_section_number=t.section_number,
                    target_hash=t.content_hash,
                    target_parent_id=t.parent_id,
                    unified_diff=diff_str,
                    diff_summary=diff_summary,
                    explanation=explanation
                )

            elif b is not None and t is None:
                # Present in base, absent in target: REMOVED
                chg_type = ChangeType.REMOVED
                comp = NodeComparison(
                    logical_id=b.logical_id,
                    change_type=chg_type,
                    matching_confidence=m.confidence,
                    is_ambiguous=m.is_ambiguous,
                    base_node_id=b.id,
                    base_title=b.title,
                    base_section_number=b.section_number,
                    base_hash=b.content_hash,
                    base_parent_id=b.parent_id,
                    explanation=f"Section {b.section_number} '{b.title}' was removed in {target_version}"
                )

            else:
                # Present in target, absent in base: ADDED
                chg_type = ChangeType.ADDED
                comp = NodeComparison(
                    logical_id=t.logical_id,
                    change_type=chg_type,
                    matching_confidence=m.confidence,
                    is_ambiguous=m.is_ambiguous,
                    target_node_id=t.id,
                    target_title=t.title,
                    target_section_number=t.section_number,
                    target_hash=t.content_hash,
                    target_parent_id=t.parent_id,
                    explanation=f"Section {t.section_number} '{t.title}' was added in {target_version}"
                )

            counts[chg_type.value] += 1
            comparisons.append(comp)

        return VersionComparisonResponse(
            base_version=base_version,
            target_version=target_version,
            total_base_nodes=len(base_nodes),
            total_target_nodes=len(target_nodes),
            summary=dict(counts),
            comparisons=comparisons
        )
