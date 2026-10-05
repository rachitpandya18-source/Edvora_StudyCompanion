def calculate_mastery(correct_answers, total_questions):
    """
    Calculate mastery score based on quiz performance.
    """

    if total_questions <= 0:
        return 0.0

    mastery = correct_answers / total_questions

    return round(mastery, 2)


def get_mastery_level(mastery):
    """
    Convert mastery score into a simple learner level.
    """

    if mastery >= 0.8:
        return "strong"

    if mastery >= 0.5:
        return "developing"

    return "weak"


def update_mastery(current_correct, current_total, is_correct):
    """
    Update learner mastery after a new question attempt.
    """

    new_correct = current_correct + (1 if is_correct else 0)
    new_total = current_total + 1

    mastery = calculate_mastery(
        new_correct,
        new_total
    )

    level = get_mastery_level(mastery)

    return {
        "correct_answers": new_correct,
        "total_questions": new_total,
        "mastery": mastery,
        "level": level
    }