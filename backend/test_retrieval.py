from app.services.ingestion_service import ingest_pdf
from app.services.retrieval_service import search_chunks


PDF_PATH = "data/uploads/physics.pdf"

# 1. Ingest PDF
chunks = ingest_pdf(
    PDF_PATH,
    "physics.pdf"
)

# 2. Ask a question
query = "What is the piezoelectric effect?"

# 3. Retrieve relevant chunks
results = search_chunks(
    chunks,
    query,
    top_k=3
)

print("\nQUERY:")
print(query)

for result in results:

    print("\n" + "=" * 70)

    print("SCORE:", result["score"])

    print("SOURCE:")
    print(result["source"])

    print("\nTEXT:")
    print(result["text"][:700])