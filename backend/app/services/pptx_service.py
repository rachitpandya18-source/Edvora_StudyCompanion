"""
PPTX Extraction Service for Edvora Study Companion.

Extracts text, slide titles, bullet points, and speaker notes from
PowerPoint presentations (.pptx) using python-pptx.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from pptx import Presentation

logger = logging.getLogger(__name__)


def extract_pptx_slides(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text slide-by-slide from a .pptx file.
    Returns a list of dictionaries with 1-based page_number (slide number)
    and combined slide text.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Presentation file not found at: {file_path}")

    try:
        prs = Presentation(str(path))
    except Exception as exc:
        logger.error(f"[PPTX_SERVICE] Failed to open presentation '{file_path}': {exc}")
        # If the file is a legacy binary .ppt or corrupted, attempt plain text extraction or raise clear error
        raise ValueError(
            f"Unable to read presentation. If this is a legacy .ppt file, please save as modern .pptx or .pdf format. ({exc})"
        ) from exc

    slides_data = []

    for slide_idx, slide in enumerate(prs.slides, start=1):
        slide_parts = []

        # Extract title if present
        if slide.shapes.title and slide.shapes.title.text:
            title_text = slide.shapes.title.text.strip()
            if title_text:
                slide_parts.append(f"Slide Title: {title_text}")

        # Extract text from all other shapes and tables
        for shape in slide.shapes:
            if shape == slide.shapes.title:
                continue

            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    para_text = paragraph.text.strip()
                    if para_text and para_text not in slide_parts:
                        slide_parts.append(para_text)

            elif shape.has_table:
                table = shape.table
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        slide_parts.append(" | ".join(row_cells))

        # Check for slide notes
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                slide_parts.append(f"Notes: {notes}")

        combined_text = "\n".join(slide_parts).strip()
        if not combined_text:
            combined_text = f"Slide {slide_idx}: Presentation Slide"

        slides_data.append({
            "page_number": slide_idx,
            "text": combined_text
        })

    if not slides_data:
        raise ValueError("Presentation contains no readable slides.")

    return slides_data
