from app.services.retrieval_service import search_chunks
from app.services.llm_service import generate_response


def answer_question(chunks, question, top_k=3):
    """
    Answer a user question using retrieved PDF context.
    """

    # 1. Retrieve relevant chunks
    results = search_chunks(
        chunks,
        question,
        top_k=top_k
    )

    if not results:
        return {
            "answer": "I could not find relevant information in the provided material.",
            "sources": []
        }

    # 2. Build context
    context_parts = []

    for result in results:

        source = result["source"]

        context_parts.append(
            f"""
SOURCE:
File: {source['filename']}
Page: {source['page']}

CONTENT:
{result['text']}
"""
        )

    context = "\n".join(context_parts)

    # 3. Grounded prompt
    prompt = f"""
You are an AI study tutor.

Answer the student's question using ONLY the provided study material.

If the answer is not present in the material, clearly say:
"I could not find this information in the provided material."

Do not invent facts.
Do not use outside knowledge.

Keep the explanation clear and student-friendly.

STUDY MATERIAL:
{context}

STUDENT QUESTION:
{question}

ANSWER:
"""

    # 4. Generate answer
    answer = generate_response(prompt)

    # 5. Preserve source metadata ourselves
    sources = []

    for result in results:

        source = result["source"]

        sources.append({
            "filename": source["filename"],
            "page": source["page"],
            "score": result["score"]
        })

    return {
        "answer": answer,
        "sources": sources
    }