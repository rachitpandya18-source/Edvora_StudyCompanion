from sentence_transformers import SentenceTransformer


# Local embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


def create_embeddings(texts):
    """
    Convert text into numerical vectors.
    """

    if not texts:
        return []

    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    )

    return embeddings