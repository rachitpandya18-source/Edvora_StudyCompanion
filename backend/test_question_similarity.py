from app.services.question_similarity_service import (
    calculate_similarity,
    is_similar_question
)


# Previously generated questions
previous_questions = [
    "What is the frequency threshold above which sound waves are classified as ultrasonic?",
    "What is the normal hearing frequency range of humans?",
    "Why do ultrasonic waves require a material medium?"
]


# Test 1: Very similar question
similar_question = (
    "Above what frequency are sound waves considered ultrasonic?"
)

print("\n===== SIMILAR QUESTION TEST =====")

similarity = calculate_similarity(
    similar_question,
    previous_questions[0]
)

print("Similarity:", round(similarity, 4))

print(
    "Is similar:",
    is_similar_question(
        similar_question,
        previous_questions
    )
)


# Test 2: Different question
different_question = (
    "How does the velocity of ultrasonic waves vary between solids and gases?"
)

print("\n===== DIFFERENT QUESTION TEST =====")

similarity = calculate_similarity(
    different_question,
    previous_questions[0]
)

print("Similarity:", round(similarity, 4))

print(
    "Is similar:",
    is_similar_question(
        different_question,
        previous_questions
    )
)