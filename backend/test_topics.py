from app.services.ingestion_service import ingest_pdf
from app.services.topic_service import extract_topics


PDF_PATH = "data/uploads/physics.pdf"
FILENAME = "physics.pdf"


# Step 1: Ingest the PDF
chunks = ingest_pdf(
    PDF_PATH,
    FILENAME
)

print(f"\nChunks created: {len(chunks)}")


# Step 2: Extract topics and concepts
result = extract_topics(chunks)


# Step 3: Display the result
print("\n===== EXTRACTED TOPICS =====\n")

for topic in result.get("topics", []):
    print(f"📚 {topic['name']}")

    for concept in topic.get("concepts", []):
        print(f"   └── {concept}")

    print()