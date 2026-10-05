import json

from app.services.llm_service import generate_response


def extract_topics(chunks):
    """
    Extract topics and concepts from document chunks using the LLM.
    """

    if not chunks:
        return {
            "topics": []
        }

    document_text = "\n\n".join(
        chunk["text"]
        for chunk in chunks
    )

    prompt = f"""
You are an educational content analyzer.

Analyze the following study material and identify its major topics
and the important concepts under each topic.

Return ONLY valid JSON in exactly this format:

{{
  "topics": [
    {{
      "name": "Topic name",
      "concepts": [
        "Concept 1",
        "Concept 2"
      ]
    }}
  ]
}}

Rules:
- Identify meaningful academic topics.
- Do not create unnecessary tiny topics.
- Concepts should be specific learning concepts.
- Use only information present in the study material.
- Do not add explanations.
- Do not use Markdown.
- Return valid JSON only.

STUDY MATERIAL:

{document_text}
"""

    response = generate_response(prompt)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        raise ValueError(
            "LLM returned invalid JSON while extracting topics."
        )