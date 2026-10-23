"""Text diffing and line change metrics."""
import difflib
from typing import Dict, Any, Tuple

class TextDiffer:
    """Computes unified diffs and summary metrics between two text versions."""

    @staticmethod
    def generate_unified_diff(
        text_a: str,
        text_b: str,
        from_label: str = "v1",
        to_label: str = "v2"
    ) -> Tuple[str, Dict[str, int]]:
        """Generate a unified diff and count added/deleted lines."""
        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)
        
        diff_lines = list(difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=from_label,
            tofile=to_label,
            lineterm=""
        ))
        
        added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        deleted = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
        
        unified_diff_str = "\n".join(diff_lines)
        summary = {"added_lines": added, "deleted_lines": deleted}
        
        return unified_diff_str, summary
