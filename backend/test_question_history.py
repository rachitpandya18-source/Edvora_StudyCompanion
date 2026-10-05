from app.services.question_history_service import (
    add_questions,
    get_question_history,
    is_question_seen,
    get_all_question_history
)


TOPIC = "Ultrasonics"
CONCEPT = "Piezoelectric Effect"


questions = [
    {
        "question": "What is the converse piezoelectric effect?"
    },
    {
        "question": "Which effect is used in a piezoelectric transducer?"
    },
    {
        "question": "What happens when an electric field is applied to a piezoelectric crystal?"
    }
]


# Add questions to history
add_questions(
    TOPIC,
    CONCEPT,
    questions
)


print("\n===== QUESTION HISTORY =====")

print(
    get_question_history(
        TOPIC,
        CONCEPT
    )
)


# Test an existing question
existing_question = (
    "What is the converse piezoelectric effect?"
)

print("\n===== EXISTING QUESTION TEST =====")

print(
    is_question_seen(
        TOPIC,
        CONCEPT,
        existing_question
    )
)


# Test a new question
new_question = (
    "How does magnetostriction generate ultrasonic waves?"
)

print("\n===== NEW QUESTION TEST =====")

print(
    is_question_seen(
        TOPIC,
        CONCEPT,
        new_question
    )
)


print("\n===== COMPLETE QUESTION HISTORY =====")

print(
    get_all_question_history()
)