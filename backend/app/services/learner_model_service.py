from app.services.mastery_service import update_mastery


# Temporary in-memory learner model.
# Later this will be replaced with a database.

learner_model = {}


def get_concept_mastery(topic, concept):
    """
    Get the current mastery data for a concept.
    """

    topic_data = learner_model.get(topic, {})

    return topic_data.get(
        concept,
        {
            "correct_answers": 0,
            "total_questions": 0,
            "mastery": 0.0,
            "level": "weak"
        }
    )


def record_answer(topic, concept, is_correct):
    """
    Record a quiz answer for a specific concept
    and update its mastery.
    """

    current = get_concept_mastery(
        topic,
        concept
    )

    updated = update_mastery(
        current_correct=current["correct_answers"],
        current_total=current["total_questions"],
        is_correct=is_correct
    )

    if topic not in learner_model:
        learner_model[topic] = {}

    learner_model[topic][concept] = updated

    return updated


def get_topic_mastery(topic):
    """
    Return mastery data for all concepts
    under a topic.
    """

    return learner_model.get(topic, {})


def get_learner_model():
    """
    Return the complete learner model.
    """

    return learner_model