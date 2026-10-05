from pathlib import Path

from app.services.ingestion_service import ingest_pdf
from app.services.topic_service import extract_topics
from app.services.quiz_service import generate_quiz


# Change ONLY this if you want to test another PDF.
PDF_PATH = "data/uploads/physics.pdf"


# Get filename automatically from the PDF path
filename = Path(PDF_PATH).name


# Step 1: Process the uploaded document
chunks = ingest_pdf(
    PDF_PATH,
    filename
)

print(f"\nDocument: {filename}")
print(f"Chunks created: {len(chunks)}")


# Step 2: Extract topics and concepts automatically
topics_result = extract_topics(chunks)

topics = topics_result.get("topics", [])

if not topics:
    raise ValueError("No topics were extracted from the document.")


# Step 3: Select the first available topic
selected_topic = topics[0]

topic_name = selected_topic["name"]
concepts = selected_topic.get("concepts", [])

if not concepts:
    raise ValueError(
        f"No concepts found for topic: {topic_name}"
    )


# Select the first concept automatically
concept_name = concepts[0]


print("\n===== SELECTED TOPIC =====")
print(f"Topic: {topic_name}")
print(f"Concept: {concept_name}")


# Step 4: Generate quiz
result = generate_quiz(
    chunks=chunks,
    topic=topic_name,
    concept=concept_name,
    num_questions=5
)


# Step 5: Display quiz
print("\n===== GENERATED QUIZ =====\n")

for index, question in enumerate(
    result.get("questions", []),
    start=1
):
    print(f"Q{index}. {question['question']}")

    for option_index, option in enumerate(
        question["options"],
        start=1
    ):
        print(f"   {option_index}. {option}")

    print(f"\n   Correct Answer: {question['correct_answer']}")
    print(f"   Difficulty: {question['difficulty']}")
    print(f"   Explanation: {question['explanation']}")
    print("   Sources:")

    for source in question["sources"]:
     print(
        f"      {source['filename']} — "
        f"Page {source['page']}"
     )

    print()