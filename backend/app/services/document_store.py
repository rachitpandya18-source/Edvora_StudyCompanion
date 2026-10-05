# Temporary in-memory document storage.
# Later we will replace this with PostgreSQL + pgvector.

documents = {}


def store_document(filename, chunks, topics=None):
    """
    Store processed document data.
    """

    documents[filename] = {
        "chunks": chunks,
        "topics": topics or []
    }


def get_document(filename):
    """
    Get processed document data.
    """

    return documents.get(filename)


def get_document_chunks(filename):
    """
    Get only the chunks of a document.
    """

    document = documents.get(filename)

    if document is None:
        return None

    return document["chunks"]


def get_document_topics(filename):
    """
    Get topics and concepts of a document.
    """

    document = documents.get(filename)

    if document is None:
        return None

    return document["topics"]


def get_all_documents():
    """
    Return all currently loaded documents.
    """

    return documents