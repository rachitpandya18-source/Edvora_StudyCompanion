from app.services.quiz_evaluation_service import evaluate_answer


# Sample generated quiz question
question = {
    "question": "What defines the frequency threshold of ultrasonic waves?",
    "options": [
        "Below 20 Hz",
        "Above approximately 20 kHz",
        "Between 20 Hz and 20 kHz",
        "Exactly 20 Hz"
    ],
    "correct_answer": "Above approximately 20 kHz",
    "explanation": "Ultrasonic waves have frequencies above the upper limit of human hearing, approximately 20 kHz.",
    "sources": [
        {
            "filename": "physics.pdf",
            "page": 1
        }
    ]
}


# Test 1: Correct answer
correct_result = evaluate_answer(
    question,
    "Above approximately 20 kHz"
)

print("\n===== CORRECT ANSWER TEST =====")
print(correct_result)


# Test 2: Wrong answer
wrong_result = evaluate_answer(
    question,
    "Below 20 Hz"
)

print("\n===== WRONG ANSWER TEST =====")
print(wrong_result)