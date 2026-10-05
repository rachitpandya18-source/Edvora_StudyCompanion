from app.services.learner_model_service import record_answer
from app.services.recommendation_service import get_recommendations


# Create some learner performance data

# Strong concept: 3/3 correct
record_answer(
    "Ultrasonics",
    "Piezoelectric Effect",
    True
)

record_answer(
    "Ultrasonics",
    "Piezoelectric Effect",
    True
)

record_answer(
    "Ultrasonics",
    "Piezoelectric Effect",
    True
)


# Weak concept: 1/3 correct
record_answer(
    "Ultrasonics",
    "Magnetostriction",
    True
)

record_answer(
    "Ultrasonics",
    "Magnetostriction",
    False
)

record_answer(
    "Ultrasonics",
    "Magnetostriction",
    False
)


# Developing concept: 2/3 correct
record_answer(
    "Ultrasonics",
    "SONAR",
    True
)

record_answer(
    "Ultrasonics",
    "SONAR",
    True
)

record_answer(
    "Ultrasonics",
    "SONAR",
    False
)


print("\n===== PERSONALIZED RECOMMENDATIONS =====")

result = get_recommendations()

print(result)