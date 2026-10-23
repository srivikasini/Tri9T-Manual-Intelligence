"""PDF Layout and Structure Extraction Pipeline."""
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pymupdf

from app.ingestion.provenance import BoundingBox, Provenance
from app.ingestion.table_parser import TableParser
from app.core.logging import logger


class RawSectionBlock:
    def __init__(
        self,
        title: str,
        section_number: Optional[str],
        level: int,
        page_start: int,
        bbox: List[float]
    ):
        self.title = title
        self.section_number = section_number
        self.level = level
        self.page_start = page_start
        self.page_end = page_start
        self.bbox = bbox
        self.text_paragraphs: List[str] = []
        self.tables: List[Dict[str, Any]] = []
        self.warnings: List[str] = []

    def get_full_text(self) -> str:
        body = "\n\n".join(p.strip() for p in self.text_paragraphs if p.strip())
        return body

class PDFExtractor:
    """Extracts text hierarchy, layout provenance, tables, and warnings from PDF manuals."""

    # Section numbering regex: e.g. "1.", "1.1", "2.1.1.1", "Section 1"
    HEADING_REGEX = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+)$")

    @classmethod
    def compute_sha256(cls, file_path: Path) -> str:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()

    @classmethod
    def is_heading(cls, span: Dict[str, Any], text: str) -> Tuple[bool, int, Optional[str], str]:
        """
        Determine if a text span represents a section heading.
        Returns (is_heading, level, section_number, clean_title).
        """
        size = round(span.get("size", 0.0), 1)
        font = span.get("font", "")
        flags = span.get("flags", 0)
        is_bold = "Bold" in font or "bold" in font or (flags & 2) != 0
        cleaned = text.strip()

        if not cleaned:
            return False, 0, None, ""

        # Normalize ligatures
        import unicodedata
        cleaned = unicodedata.normalize("NFKD", cleaned)

        # Check for title/cover
        if size >= 20.0 and is_bold:
            return True, 0, None, cleaned

        # Match section pattern e.g. "1. Device Overview" or "2.1 General Specifications"
        # Must be bold or have heading font size to distinguish from numbered list items
        match = cls.HEADING_REGEX.match(cleaned)
        if match and (is_bold or size >= 12.0):
            num = match.group(1)
            title = match.group(2).strip()
            dots = num.count(".")
            level = dots + 1
            return True, level, num, title

        # Check by font size if bold
        if is_bold and size >= 15.0:
            return True, 1, None, cleaned
        elif is_bold and size >= 12.5:
            return True, 2, None, cleaned

        return False, 0, None, ""

    @classmethod
    def extract_document(cls, pdf_path: Path, document_version: str) -> Dict[str, Any]:
        """Extract sections, paragraphs, tables, provenance, and warnings from a PDF file."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF document not found at: {pdf_path}")

        file_hash = cls.compute_sha256(pdf_path)
        doc = pymupdf.open(str(pdf_path))
        page_count = len(doc)
        
        # Extract tables via pdfplumber
        all_tables = TableParser.extract_tables_from_pdf(pdf_path)
        logger.info(f"Extracted {len(all_tables)} tables from {pdf_path.name}")

        sections: List[RawSectionBlock] = []
        current_section: Optional[RawSectionBlock] = None
        global_warnings: List[str] = []
        heading_history: List[str] = []

        # Default document-root section if no heading on page 1
        doc_root = RawSectionBlock(
            title="Document Overview",
            section_number="0",
            level=0,
            page_start=1,
            bbox=[0.0, 0.0, 0.0, 0.0]
        )

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])

            for block in blocks:
                # Type 0 is text block
                if block.get("type") != 0:
                    continue

                bbox = [round(b, 2) for b in block.get("bbox", [0, 0, 0, 0])]
                lines = block.get("lines", [])
                
                # Combine spans to inspect lines
                for line in lines:
                    line_spans = line.get("spans", [])
                    if not line_spans:
                        continue
                    
                    line_text = "".join(s.get("text", "") for s in line_spans).strip()
                    first_span = line_spans[0]
                    
                    # Check if line is a heading
                    is_hdg, level, num, title = cls.is_heading(first_span, line_text)
                    
                    if is_hdg and level > 0:
                        # New section detected
                        new_sec = RawSectionBlock(
                            title=title,
                            section_number=num,
                            level=level,
                            page_start=page_num,
                            bbox=bbox
                        )

                        # Check for irregular numbering anomalies
                        if num and heading_history:
                            prev_num = heading_history[-1]
                            # Check missing intermediate levels e.g. 2.1 to 2.1.1.1
                            curr_parts = [int(p) for p in num.split(".") if p.isdigit()]
                            prev_parts = [int(p) for p in prev_num.split(".") if p.isdigit()]
                            if len(curr_parts) > len(prev_parts) + 1:
                                warn = f"Missing intermediate heading level between {prev_num} and {num}"
                                new_sec.warnings.append(warn)
                                global_warnings.append(warn)

                            # Check out-of-order numbering (e.g. 3.2 -> 3.4 -> 3.3)
                            if len(curr_parts) == len(prev_parts) and curr_parts[:-1] == prev_parts[:-1]:
                                if curr_parts[-1] != prev_parts[-1] + 1:
                                    warn = f"Irregular/out-of-order numbering: section {num} directly followed {prev_num}"
                                    new_sec.warnings.append(warn)
                                    global_warnings.append(warn)

                        if num:
                            heading_history.append(num)

                        # Check duplicate headings across different parents
                        duplicate_matches = [s for s in sections if s.title.lower() == title.lower()]
                        if duplicate_matches:
                            warn = f"Duplicate heading title '{title}' under different parent sections (sections: {[s.section_number for s in duplicate_matches] + [num]})"
                            new_sec.warnings.append(warn)
                            global_warnings.append(warn)

                        sections.append(new_sec)
                        current_section = new_sec
                    else:
                        # Body text or table text
                        if not line_text:
                            continue
                        
                        target = current_section or doc_root
                        target.page_end = max(target.page_end, page_num)
                        
                        # Check page break continuation
                        if page_num > target.page_start and not target.text_paragraphs:
                            warn = f"Content continues across page boundary onto page {page_num}"
                            if warn not in target.warnings:
                                target.warnings.append(warn)
                                
                        # Append line or combine wrapped lines
                        if target.text_paragraphs and not target.text_paragraphs[-1].endswith((".", ":", ";", "!", "?")):
                            target.text_paragraphs[-1] += " " + line_text
                        else:
                            target.text_paragraphs.append(line_text)

        # If sections list is empty (fallback), use doc_root
        if not sections:
            sections.append(doc_root)

        # Associate extracted tables to sections based on page number and vertical position
        for tbl in all_tables:
            tbl_page = tbl["page"]
            tbl_y0 = tbl["bbox"][1] if tbl.get("bbox") else 0.0

            # Find sections spanning or starting on this page
            page_secs = [s for s in sections if s.page_start <= tbl_page <= s.page_end]
            if page_secs:
                # Headings on this page that appear before the table vertically
                candidates = [s for s in page_secs if s.bbox[1] <= tbl_y0]
                if candidates:
                    candidates[-1].tables.append(tbl)
                else:
                    page_secs[0].tables.append(tbl)
            else:
                prior_secs = [s for s in sections if s.page_start <= tbl_page]
                if prior_secs:
                    prior_secs[-1].tables.append(tbl)

        return {
            "document_id": "ct200_manual",
            "version_id": document_version,
            "filename": pdf_path.name,
            "file_hash": file_hash,
            "page_count": page_count,
            "raw_sections": sections,
            "global_warnings": global_warnings,
            "tables_count": len(all_tables)
        }
