# Temporary in-memory question history.
# Later this will be stored in the database.

question_history = {}


def get_question_history(topic, concept):
    """
    Return previously generated questions
    for a specific topic and concept.
    """

    topic_data = question_history.get(topic, {})

    return topic_data.get(concept, [])


def add_questions(topic, concept, questions):
    """
    Store generated questions for a topic and concept.
    """

    if topic not in question_history:
        question_history[topic] = {}

    if concept not in question_history[topic]:
        question_history[topic][concept] = []

    for question in questions:

        question_text = question["question"]

        # Avoid storing the same question twice
        if question_text not in question_history[topic][concept]:
            question_history[topic][concept].append(
                question_text
            )


def is_question_seen(topic, concept, question_text):
    """
    Check whether a question has already been generated.
    """

    previous_questions = get_question_history(
        topic,
        concept
    )

    return question_text in previous_questions


def get_all_question_history():
    """
    Return the complete question history.
    """

    return question_history