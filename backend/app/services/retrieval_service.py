import numpy as np

from app.services.embedding_service import create_embeddings


def search_chunks(chunks, query, top_k=3):
    """
    Find the chunks that are semantically most relevant
    to the user's query.
    """

    if not chunks:
        return []

    chunk_texts = [chunk["text"] for chunk in chunks]

    # Create embeddings
    chunk_embeddings = create_embeddings(chunk_texts)

    # Create query embedding
    query_embedding = create_embeddings([query])[0]

    # Calculate cosine similarity
    scores = np.dot(chunk_embeddings, query_embedding)

    # Highest similarity first
    ranked_indices = np.argsort(scores)[::-1]

    results = []

    for index in ranked_indices[:top_k]:
        result = chunks[index].copy()

        result["score"] = float(scores[index])

        results.append(result)

    return results