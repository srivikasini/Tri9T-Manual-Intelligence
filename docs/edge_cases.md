# Edge Cases & Limitations Reference — Tri9T Manual Intelligence Platform

This document catalogs the document processing, structural normalization, and layout edge cases handled by the platform, detailing both the detection mechanisms and system limitations.

---

## 1. Document Extraction Edge Cases

### Edge Case 1: Missing Intermediate Heading Levels
- **Occurrence**: In `ct200_manual.pdf` (Page 2), Section `2.1 General Specifications` is directly followed by Section `2.1.1.1 Battery Life Under Typical Use`. Intermediate heading `2.1.1` does not exist in the document.
- **Handling**:
  - The `HierarchyTreeBuilder` inspects dot-separated numerical prefixes. When `2.1.1` is not found, the resolver traverses upwards to the closest existing ancestor (`2.1`).
  - An extraction warning is recorded: `"Missing intermediate heading level between 2.1 and 2.1.1.1"`.
  - The node is safely linked under `2.1` while preserving its true Level 4 heading metadata without fabricating synthetic parent nodes.

### Edge Case 2: Irregular and Out-of-Order Section Numbering
- **Occurrence**: In `ct200_manual.pdf` (Page 3), Section `3.2 Cuff Inflation Sequence` is immediately followed by Section `3.4 Auto Shutoff`, which is then followed by Section `3.3 Result Display and Classification`.
- **Handling**:
  - The extractor tracks historical section sequences. When a non-monotonic transition is detected (e.g. 3.2 -> 3.4), an anomaly warning is registered: `"Irregular/out-of-order numbering: section 3.4 directly followed 3.2"`.
  - Reading order is preserved based on physical page sequence and vertical coordinates (`y0`), rather than forcing artificial reordering that would distort the user's manual layout.

### Edge Case 3: Duplicate Heading Titles Under Different Parents
- **Occurrence**: Both Section `4.2` (under *4. Alarms and Safety Behavior*) and Section `7.1` (under *7. Troubleshooting*) are titled `"Error Codes"`.
- **Handling**:
  - The platform strictly enforces that section titles alone are never used as identifiers.
  - Distinct stable logical IDs are generated: `sec:4.2:error-codes` and `sec:7.1:error-codes`.
  - A duplicate title warning is recorded: `"Duplicate heading title 'Error Codes' under different parent sections (sections: ['4.2', '7.1'])"`.
  - Content hashes, diffs, and selections distinguish between them without ambiguity.

### Edge Case 4: Page-Break Text Continuation
- **Occurrence**: In `ct200_manual_v2.pdf`:
  - Section `4.3 Alarm Thresholds` starts at the bottom of Page 4 and its sentence finishes at the top of Page 5: `"(overpressure), which cannot be silenced for safety reasons."`
  - Section `6.1 Cleaning Instructions` starts at the bottom of Page 5 and finishes at the top of Page 6: `"use alcohol, solvents, or abrasive cleaners on the display."`
  - Section `8.1 Classification` starts at the bottom of Page 6 and finishes on Page 7.
- **Handling**:
  - Blocks starting at the top of a page with lowercase text or without intervening section headers are detected as continuations of the active section.
  - Text is joined cleanly across the page boundary, and `page_end` is updated to reflect the multi-page span.
  - Bounding boxes reflect both starting and ending page coordinates.

### Edge Case 5: Table Cell Text Wrapping & Spurious Fragment Filtering
- **Occurrence**:
  - In Section `4.2`, table cells wrap long sentences across multiple lines (e.g. `"Aborts measurement, displays E2, prompts retry"`).
  - In Section `2.1`, table lines produce one-row visual fragments (e.g. border coordinates parsed as isolated 1-row boxes).
- **Handling**:
  - `table_parser.py` collapses multi-line wrapped cells by normalizing inner newlines.
  - Spurious fragments (tables with fewer than 3 total rows or fewer than 2 valid columns) are filtered out, leaving only genuine data grids.
  - Each primary table is attached to its enclosing section using vertical coordinate proximity (`y0_heading <= y0_table`).

### Edge Case 6: Unicode Ligatures and Non-Breaking Characters
- **Occurrence**: Technical typography in the PDF manuals includes ligatures (`\ufb01` for `fi`, `\ufb02` for `fl`) and non-breaking hyphens (`\u2011`).
- **Handling**:
  - Text normalization applies Unicode NFKD normalization across all extracted blocks.
  - Terminal outputs and log streams explicitly reconfigure standard output encoding to UTF-8, preventing Windows cp1252 `UnicodeEncodeError` exceptions.

---

## 2. Known Limitations & Unsupported Scenarios

1. **Scanned Bitmaps Without OCR**:
   - The current pipeline relies on native vector text extraction via PyMuPDF. If a document is a pure scanned raster image with zero OCR text layer, PyMuPDF yields 0 blocks. (Selectable OCR via Tesseract can be plugged into the extraction stage if needed).
2. **Complex Multi-Column Newspapers**:
   - The extractor orders blocks top-to-bottom by `y0`. For complex multi-column newspaper layouts with interwoven sidebars, custom column segmentation algorithms would be needed.
3. **Complex Nested Tables**:
   - Multi-level nested tables with merged horizontal and vertical headers are flattened into clean 2D tabular rows.
