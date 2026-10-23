"""Staleness and Impact Analysis Engine."""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.qa_artifact import QAArtifact
from app.models.node import SectionNode
from app.schemas.staleness import (
    StalenessSeverity,
    DriftType,
    StalenessReasonItem,
    StalenessCheckResponse
)
from app.diffing.differ import TextDiffer
from app.diffing.matcher import CrossVersionMatcher

class StalenessAnalyzer:
    """Evaluates whether QA artifacts generated on an earlier document version are stale."""

    @staticmethod
    def _assess_impact_severity(old_text: str, new_text: str) -> StalenessSeverity:
        """
        Assess severity based on whether numerical values, error codes,
        safety conditions, or tolerances changed.
        """
        # Extract numerical quantities and error codes
        old_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", old_text))
        new_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", new_text))
        
        old_codes = set(re.findall(r"\bE\d\b", old_text))
        new_codes = set(re.findall(r"\bE\d\b", new_text))

        # Critical changes: numerical parameters or error codes changed
        if old_numbers != new_numbers or old_codes != new_codes:
            return StalenessSeverity.HIGH

        # Critical safety terms
        safety_keywords = {"warning", "caution", "danger", "abort", "deflate", "exceed", "contraindication"}
        old_has_safety = any(kw in old_text.lower() for kw in safety_keywords)
        new_has_safety = any(kw in new_text.lower() for kw in safety_keywords)
        if old_has_safety != new_has_safety:
            return StalenessSeverity.HIGH

        # If significant word modifications exist
        words_old = set(old_text.lower().split())
        words_new = set(new_text.lower().split())
        jaccard = len(words_old.intersection(words_new)) / len(words_old.union(words_new)) if words_old and words_new else 1.0

        if jaccard < 0.80:
            return StalenessSeverity.MEDIUM
        return StalenessSeverity.LOW

    @classmethod
    def evaluate_artifact_staleness(
        cls,
        artifact: QAArtifact,
        target_version: str,
        db: Session
    ) -> StalenessCheckResponse:
        """
        Compare an artifact's stored source snapshots and hashes against nodes in the target version.
        """
        stored_snapshots: Dict[str, str] = json.loads(artifact.source_snapshots_json)
        stored_hashes: Dict[str, str] = json.loads(artifact.source_hashes_json)
        source_node_ids: List[str] = json.loads(artifact.source_node_ids_json)

        # Retrieve target version nodes
        target_nodes = db.query(SectionNode).filter(SectionNode.document_version == target_version).all()
        target_by_logical = {n.logical_id: n for n in target_nodes}

        # Also retrieve the original nodes from artifact's base version for metadata
        base_nodes = db.query(SectionNode).filter(SectionNode.id.in_(source_node_ids)).all()
        base_node_map = {n.id: n for n in base_nodes}

        reasons: List[StalenessReasonItem] = []
        highest_severity = StalenessSeverity.NONE

        for n_id in source_node_ids:
            stored_hash = stored_hashes.get(n_id, "")
            stored_text = stored_snapshots.get(n_id, "")
            base_node = base_node_map.get(n_id)

            if not base_node:
                # Node record missing from database
                reasons.append(StalenessReasonItem(
                    node_id=n_id,
                    logical_id="unknown",
                    drift_type=DriftType.NODE_REMOVED,
                    severity=StalenessSeverity.HIGH,
                    description=f"Original source node {n_id} cannot be resolved in database.",
                    stored_hash=stored_hash
                ))
                highest_severity = StalenessSeverity.HIGH
                continue

            logical_id = base_node.logical_id
            target_node = target_by_logical.get(logical_id)

            if target_node is None:
                # Node disappeared or logical ID changed
                # Attempt heuristic match across target nodes
                matches = CrossVersionMatcher.match_nodes([base_node], target_nodes)
                matched_cand = matches[0].target_node if matches else None

                if matched_cand is not None:
                    # Node was moved or renamed
                    diff_text, _ = TextDiffer.generate_unified_diff(stored_text, matched_cand.full_text)
                    sev = cls._assess_impact_severity(stored_text, matched_cand.full_text)
                    reasons.append(StalenessReasonItem(
                        node_id=n_id,
                        logical_id=logical_id,
                        drift_type=DriftType.NODE_MOVED,
                        severity=sev,
                        description=(
                            f"Node {base_node.section_number} ('{base_node.title}') was relocated or renamed to "
                            f"{matched_cand.section_number} ('{matched_cand.title}')."
                        ),
                        stored_hash=stored_hash,
                        current_hash=matched_cand.content_hash,
                        text_diff=diff_text
                    ))
                    if sev == StalenessSeverity.HIGH or (sev == StalenessSeverity.MEDIUM and highest_severity != StalenessSeverity.HIGH):
                        highest_severity = sev
                else:
                    # Node completely removed
                    reasons.append(StalenessReasonItem(
                        node_id=n_id,
                        logical_id=logical_id,
                        drift_type=DriftType.NODE_REMOVED,
                        severity=StalenessSeverity.HIGH,
                        description=f"Node {base_node.section_number} ('{base_node.title}') was removed in {target_version}.",
                        stored_hash=stored_hash
                    ))
                    highest_severity = StalenessSeverity.HIGH

            else:
                # Node exists in target version: compare hashes
                if target_node.content_hash != stored_hash:
                    diff_text, diff_sum = TextDiffer.generate_unified_diff(
                        stored_text,
                        target_node.full_text,
                        from_label=f"{artifact.document_version}:{base_node.section_number}",
                        to_label=f"{target_version}:{target_node.section_number}"
                    )
                    sev = cls._assess_impact_severity(stored_text, target_node.full_text)
                    reasons.append(StalenessReasonItem(
                        node_id=n_id,
                        logical_id=logical_id,
                        drift_type=DriftType.HASH_DRIFT,
                        severity=sev,
                        description=(
                            f"Content drift detected in Section {target_node.section_number} ('{target_node.title}'): "
                            f"+{diff_sum['added_lines']} lines, -{diff_sum['deleted_lines']} lines."
                        ),
                        stored_hash=stored_hash,
                        current_hash=target_node.content_hash,
                        text_diff=diff_text
                    ))
                    if sev == StalenessSeverity.HIGH or (sev == StalenessSeverity.MEDIUM and highest_severity != StalenessSeverity.HIGH):
                        highest_severity = sev
                else:
                    # Identical hash: check structural relocation
                    base_parent_logical = base_node.parent.logical_id if base_node.parent else None
                    target_parent_logical = target_node.parent.logical_id if target_node.parent else None
                    if target_node.section_number != base_node.section_number or target_parent_logical != base_parent_logical:
                        reasons.append(StalenessReasonItem(
                            node_id=n_id,
                            logical_id=logical_id,
                            drift_type=DriftType.NODE_MOVED,
                            severity=StalenessSeverity.LOW,
                            description=f"Content unchanged, but section shifted from {base_node.section_number} to {target_node.section_number}.",
                            stored_hash=stored_hash,
                            current_hash=target_node.content_hash
                        ))
                        if highest_severity == StalenessSeverity.NONE:
                            highest_severity = StalenessSeverity.LOW

        is_stale = len(reasons) > 0
        if is_stale:
            recommendation = (
                f"Artifact has {len(reasons)} affected source node(s) with {highest_severity.value} severity. "
                "Regeneration against current version is recommended to preserve test veracity."
            )
        else:
            recommendation = "All source nodes match current version identically. Artifact remains verified and valid."

        return StalenessCheckResponse(
            artifact_id=artifact.id,
            selection_id=artifact.selection_id,
            base_version=artifact.document_version,
            target_version=target_version,
            is_stale=is_stale,
            overall_severity=highest_severity,
            total_source_nodes=len(source_node_ids),
            affected_nodes_count=len(reasons),
            reasons=reasons,
            recommendation=recommendation,
            checked_at=datetime.now(timezone.utc)
        )
