from app.services.pdf_service import extract_pdf_pages
from app.services.chunk_service import chunk_text


def ingest_pdf(file_path: str, filename: str):
    """
    Extract a PDF page-by-page and convert it into
    chunks while preserving source information.
    """

    pages = extract_pdf_pages(file_path)

    chunks = []

    for page in pages:

        page_chunks = chunk_text(page["text"])

        for index, chunk in enumerate(page_chunks):

            chunks.append({
                "id": f"{filename}_page_{page['page_number']}_chunk_{index}",

                "text": chunk,

                "source": {
                    "type": "pdf",
                    "filename": filename,
                    "page": page["page_number"]
                }
            })

    return chunks