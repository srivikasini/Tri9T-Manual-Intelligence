"""Provenance data structures for tracking source page, bounding box, and location."""
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def to_list(self) -> List[float]:
        return [round(self.x0, 2), round(self.y0, 2), round(self.x1, 2), round(self.y1, 2)]

@dataclass
class Provenance:
    page_start: int
    page_end: int
    bbox: Optional[BoundingBox] = None
    order_index: int = 0
