from pathlib import Path

from app.services.ingestion_service import ingest_pdf
from app.services.quiz_service import generate_quiz
from app.services.question_history_service import get_question_history


PDF_PATH = "data/uploads/physics.pdf"

filename = Path(PDF_PATH).name

# Process document
chunks = ingest_pdf(
    PDF_PATH,
    filename
)

topic = "Ultrasonics Introduction and Fundamentals"
concept = "Definition and frequency range of ultrasonic waves"


print("\n===== FIRST QUIZ =====")

quiz1 = generate_quiz(
    chunks=chunks,
    topic=topic,
    concept=concept,
    num_questions=5
)

for index, question in enumerate(
    quiz1.get("questions", []),
    start=1
):
    print(f"{index}. {question['question']}")


print("\n===== QUESTION HISTORY AFTER FIRST QUIZ =====")

history = get_question_history(
    topic,
    concept
)

for question in history:
    print("-", question)


print("\n===== SECOND QUIZ =====")

quiz2 = generate_quiz(
    chunks=chunks,
    topic=topic,
    concept=concept,
    num_questions=5
)

for index, question in enumerate(
    quiz2.get("questions", []),
    start=1
):
    print(f"{index}. {question['question']}")


print("\n===== FINAL QUESTION HISTORY =====")

history = get_question_history(
    topic,
    concept
)

print(f"Total stored questions: {len(history)}")