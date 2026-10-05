from app.services.ingestion_service import ingest_pdf


PDF_PATH = "data/uploads/physics.pdf"

chunks = ingest_pdf(
    PDF_PATH,
    "physics.pdf"
)

print(f"Total chunks: {len(chunks)}")

for chunk in chunks[:5]:

    print("\n" + "=" * 70)

    print("ID:", chunk["id"])

    print("SOURCE:")
    print(chunk["source"])

    print("\nTEXT:")
    print(chunk["text"][:500])