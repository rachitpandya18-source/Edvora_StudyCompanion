import numpy as np
from sentence_transformers import SentenceTransformer

# Expected vector dimension for all-MiniLM-L6-v2
EMBEDDING_DIM = 384

# Local embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


def create_embeddings(texts):
    """
    Convert text into numerical vectors.
    Returns normalized float32 embeddings.
    """
    if not texts:
        return []

    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    )

    return embeddings


def validate_embedding_vector(vector, expected_dim: int = EMBEDDING_DIM) -> bool:
    """
    Verify that an embedding is a valid finite float array of the expected dimension.
    """
    if vector is None:
        return False
    if not isinstance(vector, (np.ndarray, list)):
        return False
    arr = np.asarray(vector, dtype=np.float32)
    if arr.ndim != 1 or arr.shape[0] != expected_dim:
        return False
    if not np.all(np.isfinite(arr)):
        return False
    return True


def serialize_embedding(vector) -> bytes:
    """
    Serialize a 384-dimensional normalized float32 vector into compact binary bytes.
    384 float32 values = 1,536 bytes.
    """
    if not validate_embedding_vector(vector, EMBEDDING_DIM):
        raise ValueError(
            f"Embedding must be a valid 1D array of dimension {EMBEDDING_DIM}."
        )
    arr = np.asarray(vector, dtype=np.float32)
    return arr.tobytes()


def deserialize_embedding(blob: bytes) -> np.ndarray:
    """
    Deserialize compact binary bytes into a normalized 384-dimensional float32 NumPy array.
    """
    if not blob:
        raise ValueError("Cannot deserialize empty embedding blob.")
    expected_bytes = EMBEDDING_DIM * 4  # 4 bytes per float32
    if len(blob) != expected_bytes:
        raise ValueError(
            f"Expected {expected_bytes} bytes for {EMBEDDING_DIM}-dim float32 embedding, "
            f"got {len(blob)} bytes."
        )
    arr = np.frombuffer(blob, dtype=np.float32)
    return arr