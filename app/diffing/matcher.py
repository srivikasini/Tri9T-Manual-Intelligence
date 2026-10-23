"""Cross-version node matching using structural context, heading similarity, and content overlap."""
import difflib
from typing import List, Dict, Any, Tuple, Optional, Set

def text_similarity(s1: str, s2: str) -> float:
    """Compute string similarity ratio between 0.0 and 1.0."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

def token_jaccard_similarity(text1: str, text2: str) -> float:
    """Compute token-level Jaccard similarity."""
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union if union > 0 else 0.0

class NodeMatchResult:
    def __init__(
        self,
        base_node: Optional[Any],
        target_node: Optional[Any],
        confidence: float,
        is_ambiguous: bool = False,
        match_type: str = "EXACT_LOGICAL_ID"
    ):
        self.base_node = base_node
        self.target_node = target_node
        self.confidence = confidence
        self.is_ambiguous = is_ambiguous
        self.match_type = match_type

class CrossVersionMatcher:
    """Matches logically equivalent nodes across two document versions."""

    @classmethod
    def match_nodes(
        cls,
        base_nodes: List[Any],
        target_nodes: List[Any]
    ) -> List[NodeMatchResult]:
        """
        Produce a list of NodeMatchResults covering matched pairs, additions, and removals.
        """
        matched_results: List[NodeMatchResult] = []
        target_by_logical = {n.logical_id: n for n in target_nodes}
        matched_target_ids: Set[str] = set()
        matched_base_ids: Set[str] = set()

        # Phase 1: Exact logical ID match
        for b_node in base_nodes:
            if b_node.logical_id in target_by_logical:
                t_node = target_by_logical[b_node.logical_id]
                matched_results.append(NodeMatchResult(
                    base_node=b_node,
                    target_node=t_node,
                    confidence=1.0,
                    is_ambiguous=False,
                    match_type="EXACT_LOGICAL_ID"
                ))
                matched_base_ids.add(b_node.id)
                matched_target_ids.add(t_node.id)

        # Phase 2: Heuristic matching for unmatched base nodes
        unmatched_base = [b for b in base_nodes if b.id not in matched_base_ids]
        unmatched_target = [t for t in target_nodes if t.id not in matched_target_ids]

        for b_node in unmatched_base:
            candidate_scores: List[Tuple[Any, float, str]] = []

            for t_node in unmatched_target:
                if t_node.id in matched_target_ids:
                    continue

                # Check 1: Same section number, similar title (renamed)
                if b_node.section_number and b_node.section_number == t_node.section_number:
                    title_sim = text_similarity(b_node.title, t_node.title)
                    score = 0.85 + 0.15 * title_sim
                    candidate_scores.append((t_node, score, "RENAMED_HEADING"))
                    continue

                # Check 2: Same title, different section number (moved)
                title_sim = text_similarity(b_node.title, t_node.title)
                if title_sim > 0.85:
                    content_sim = token_jaccard_similarity(b_node.full_text, t_node.full_text)
                    score = 0.70 + 0.30 * content_sim
                    candidate_scores.append((t_node, score, "MOVED_SECTION"))
                    continue

                # Check 3: Content similarity (both title and section changed)
                content_sim = token_jaccard_similarity(b_node.full_text, t_node.full_text)
                if content_sim >= 0.70:
                    score = 0.60 + 0.30 * content_sim
                    candidate_scores.append((t_node, score, "SEMANTIC_CONTENT_OVERLAP"))

            if candidate_scores:
                # Sort candidates by score descending
                candidate_scores.sort(key=lambda x: x[1], reverse=True)
                best_target, best_score, match_type = candidate_scores[0]

                # Check ambiguity: is there a second candidate close to the best?
                is_ambiguous = False
                if len(candidate_scores) > 1 and (best_score - candidate_scores[1][1]) < 0.10:
                    is_ambiguous = True

                if best_score >= 0.65:
                    matched_results.append(NodeMatchResult(
                        base_node=b_node,
                        target_node=best_target,
                        confidence=round(best_score, 2),
                        is_ambiguous=is_ambiguous,
                        match_type=match_type
                    ))
                    matched_base_ids.add(b_node.id)
                    matched_target_ids.add(best_target.id)
                else:
                    # Confidence too low: treat as REMOVED
                    matched_results.append(NodeMatchResult(
                        base_node=b_node,
                        target_node=None,
                        confidence=1.0,
                        is_ambiguous=False,
                        match_type="REMOVED"
                    ))
                    matched_base_ids.add(b_node.id)
            else:
                # No candidates: REMOVED
                matched_results.append(NodeMatchResult(
                    base_node=b_node,
                    target_node=None,
                    confidence=1.0,
                    is_ambiguous=False,
                    match_type="REMOVED"
                ))
                matched_base_ids.add(b_node.id)

        # Phase 3: Remaining unmatched target nodes are ADDED
        for t_node in target_nodes:
            if t_node.id not in matched_target_ids:
                matched_results.append(NodeMatchResult(
                    base_node=None,
                    target_node=t_node,
                    confidence=1.0,
                    is_ambiguous=False,
                    match_type="ADDED"
                ))

        return matched_results
