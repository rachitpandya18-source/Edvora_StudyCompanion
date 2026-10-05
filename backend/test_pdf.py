from app.services.pdf_service import extract_pdf_pages


PDF_PATH = "data/uploads/physics.pdf"

pages = extract_pdf_pages(PDF_PATH)

print(f"Total pages: {len(pages)}")

for page in pages[:3]:
    print("\n" + "=" * 60)
    print(f"PAGE {page['page_number']}")
    print("=" * 60)
    print(page["text"][:1000])