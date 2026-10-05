from app.services.pdf_service import extract_pdf_pages

PDF_PATH = "data/uploads/chemistry.pdf"

pages = extract_pdf_pages(PDF_PATH)

for page in pages:
    print("\n" + "=" * 80)
    print(f"PAGE {page['page_number']}")
    print("=" * 80)
    print(page["text"])