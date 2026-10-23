"""Diffing and version comparison package exports."""
from app.diffing.differ import TextDiffer
from app.diffing.matcher import CrossVersionMatcher, NodeMatchResult, text_similarity, token_jaccard_similarity
from app.diffing.change_detector import ChangeDetector

__all__ = [
    "TextDiffer",
    "CrossVersionMatcher",
    "NodeMatchResult",
    "text_similarity",
    "token_jaccard_similarity",
    "ChangeDetector"
]
