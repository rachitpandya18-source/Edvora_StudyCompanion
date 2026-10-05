from app.services.learner_model_service import (
    record_answer,
    get_concept_mastery,
    get_topic_mastery,
    get_learner_model
)


TOPIC = "Introduction and Fundamentals of Ultrasonics"
CONCEPT = "Definition and frequency range of ultrasonic waves"


print("\n===== INITIAL MASTERY =====")

print(
    get_concept_mastery(
        TOPIC,
        CONCEPT
    )
)


# Student answers 3 questions:
# 1 correct
# 2 correct
# 3 wrong

record_answer(
    TOPIC,
    CONCEPT,
    True
)

record_answer(
    TOPIC,
    CONCEPT,
    True
)

record_answer(
    TOPIC,
    CONCEPT,
    False
)


print("\n===== AFTER 3 ANSWERS =====")

print(
    get_concept_mastery(
        TOPIC,
        CONCEPT
    )
)


print("\n===== TOPIC MASTERY =====")

print(
    get_topic_mastery(TOPIC)
)


print("\n===== COMPLETE LEARNER MODEL =====")

print(
    get_learner_model()
)