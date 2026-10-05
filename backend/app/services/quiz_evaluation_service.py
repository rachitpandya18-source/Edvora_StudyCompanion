def evaluate_answer(question, selected_answer):
    """
    Evaluate a student's answer for a generated quiz question.
    """

    correct_answer = question["correct_answer"]

    # Normalize answers for comparison
    selected_normalized = selected_answer.strip().lower()
    correct_normalized = correct_answer.strip().lower()

    is_correct = selected_normalized == correct_normalized

    return {
        "is_correct": is_correct,
        "selected_answer": selected_answer,
        "correct_answer": correct_answer,
        "explanation": question.get("explanation", ""),
        "sources": question.get("sources", [])
    }