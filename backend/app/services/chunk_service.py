def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120):
    """
    Split text into overlapping chunks.

    chunk_size and overlap are measured in words.
    """

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = min(start + chunk_size, len(words))

        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = end - overlap

    return chunks