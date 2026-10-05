from app.services.ingestion_service import ingest_pdf
from app.services.rag_service import answer_question


PDF_PATH = "data/uploads/physics.pdf"


# 1. Ingest PDF
chunks = ingest_pdf(
    PDF_PATH,
    "physics.pdf"
)


# 2. Ask question
question = "What is the piezoelectric effect?"


# 3. Generate grounded answer
result = answer_question(
    chunks,
    question,
    top_k=3
)


# 4. Print answer
print("\n" + "=" * 70)
print("QUESTION:")
print(question)

print("\n" + "=" * 70)
print("ANSWER:")
print(result["answer"])


# 5. Print sources
print("\n" + "=" * 70)
print("SOURCES:")

for source in result["sources"]:
    print(
        f"- {source['filename']} | "
        f"Page {source['page']} | "
        f"Score: {source['score']:.4f}"
    )

print("=" * 70)