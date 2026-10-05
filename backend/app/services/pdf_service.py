import pymupdf
from pypdf import PdfReader


def extract_pdf_pages(file_path: str):
    """
    Extract text page-by-page from a PDF.

    PyMuPDF is used as the primary extractor because
    it generally preserves PDF text layout and Unicode
    characters better.

    pypdf is kept as a fallback.
    """

    pages = []

    try:
        # --------------------------------------------------
        # Primary extraction: PyMuPDF
        # --------------------------------------------------

        document = pymupdf.open(file_path)

        for page_number, page in enumerate(
            document,
            start=1
        ):
            text = page.get_text(
                "text",
                sort=True
            )

            pages.append({
                "page_number": page_number,
                "text": text.strip()
            })

        document.close()

        return pages

    except Exception as error:

        print(
            f"[PDF] PyMuPDF extraction failed: {error}"
        )

        print(
            "[PDF] Falling back to pypdf..."
        )

        # --------------------------------------------------
        # Fallback extraction: pypdf
        # --------------------------------------------------

        reader = PdfReader(file_path)

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):
            text = page.extract_text() or ""

            pages.append({
                "page_number": page_number,
                "text": text.strip()
            })

        return pages