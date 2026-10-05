from app.services.learner_model_service import get_learner_model


def get_weak_concepts():
    """
    Find concepts where the learner needs more practice.
    """

    learner_model = get_learner_model()

    weak_concepts = []

    for topic, concepts in learner_model.items():

        for concept, data in concepts.items():

            if data["level"] == "weak":
                weak_concepts.append({
                    "topic": topic,
                    "concept": concept,
                    "mastery": data["mastery"],
                    "recommendation": "Practice this concept"
                })

    return weak_concepts


def get_recommendations():
    """
    Generate personalized learning recommendations.
    """

    weak_concepts = get_weak_concepts()

    return {
        "weak_concepts": weak_concepts,
        "total_weak_concepts": len(weak_concepts)
    }
