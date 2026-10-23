"""Table extraction and normalization from PDF documents."""
from typing import List, Dict, Any, Optional
import pdfplumber
from pathlib import Path

class TableParser:
    """Extracts and normalizes multi-row tables from PDF pages."""
    
    @staticmethod
    def extract_tables_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract multi-row structured tables with page numbers and cell data."""
        extracted_tables = []
        
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_num = page_index + 1
                tables = page.extract_tables()
                
                # We can also get table bounding boxes using find_tables()
                found_tables = page.find_tables()
                
                for idx, t in enumerate(tables):
                    if not t or len(t) < 2:
                        continue
                    
                    # Clean up cells: strip whitespace and internal newlines
                    cleaned_grid = []
                    for row in t:
                        clean_row = [
                            " ".join(cell.split()) if cell else ""
                            for cell in row
                        ]
                        if any(clean_row):  # skip completely empty rows
                            cleaned_grid.append(clean_row)
                            
                    # Filter out spurious fragments (need at least 3 valid rows and at least 2 non-empty header columns)
                    non_empty_headers = [c for c in cleaned_grid[0] if c]
                    if len(cleaned_grid) < 3 or len(non_empty_headers) < 2:
                        continue
                    
                    headers = cleaned_grid[0]
                    rows = cleaned_grid[1:]
                    
                    # Find bbox if available
                    bbox = None
                    if idx < len(found_tables):
                        t_bbox = found_tables[idx].bbox
                        bbox = [round(v, 2) for v in t_bbox]
                        
                    extracted_tables.append({
                        "page": page_num,
                        "headers": headers,
                        "rows": rows,
                        "bbox": bbox
                    })
                    
        return extracted_tables
