import numpy as np

from app.services.embedding_service import create_embeddings


SIMILARITY_THRESHOLD = 0.85


def calculate_similarity(question_a, question_b):
    """
    Calculate semantic similarity between two questions.
    """

    embeddings = create_embeddings([
        question_a,
        question_b
    ])

    similarity = np.dot(
        embeddings[0],
        embeddings[1]
    )

    return float(similarity)


def is_similar_question(
    new_question,
    previous_questions,
    threshold=SIMILARITY_THRESHOLD
):
    """
    Check whether a new question is semantically
    similar to any previously generated question.
    """

    if not previous_questions:
        return False

    new_embedding = create_embeddings([
        new_question
    ])[0]

    previous_embeddings = create_embeddings(
        previous_questions
    )

    similarities = np.dot(
        previous_embeddings,
        new_embedding
    )

    highest_similarity = float(
        np.max(similarities)
    )

    return highest_similarity >= threshold