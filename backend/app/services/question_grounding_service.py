import json

from app.services.llm_service import generate_response


def _parse_json_response(response):
    cleaned_response = response.strip()

    # Remove Markdown code fences
    if cleaned_response.startswith("```"):
        lines = cleaned_response.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned_response = "\n".join(lines).strip()

    try:
        return json.loads(cleaned_response)
    except json.JSONDecodeError as error:
        print("[GROUNDING] Invalid JSON returned by verifier.")
        print(f"[GROUNDING] Raw response: {response}")
        print(f"[GROUNDING] JSON error: {error}")

        return None


def check_questions_grounding(
    questions,
    document_context,
):
    """
    Verify multiple generated questions in ONE LLM call.

    Returns a list of:
    {
        "grounded": True/False,
        "reason": "..."
    }
    """

    if not questions:
        return []

    questions_text = []

    for index, question in enumerate(questions):

        questions_text.append(
            f"""
QUESTION {index}:

Question:
{question["question"]}

Options:
{json.dumps(question["options"], ensure_ascii=False)}

Correct Answer:
{question["correct_answer"]}

Explanation:
{question["explanation"]}
"""
        )

    all_questions = "\n".join(questions_text)

    prompt = f"""
You are a strict educational content verifier.

Verify whether each multiple-choice question below is
fully supported by the provided study material.

==================================================
STUDY MATERIAL
==================================================

{document_context}

==================================================
QUESTIONS TO VERIFY
==================================================

{all_questions}

==================================================
GROUNDING RULES
==================================================

A question is grounded ONLY when:

1. The question can be answered using the study material.
2. The correct answer is supported by the study material.
3. The explanation is supported by the study material.
4. The question does not require outside knowledge.
5. The question does not introduce facts absent from
   the study material.

If a question is generally true but the study material
does not support it, mark it as false.

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

Do NOT use Markdown.

Do NOT use ```json.

Use exactly this structure:

{{
  "results": [
    {{
      "index": 0,
      "grounded": true,
      "reason": "Short explanation"
    }},
    {{
      "index": 1,
      "grounded": false,
      "reason": "Short explanation"
    }}
  ]
}}

Rules:

- Include exactly one result for every question.
- Use the original question index.
- grounded must be either true or false.
- Do not add extra fields.
"""

    try:
        response = generate_response(prompt)
    except Exception as error:
        print("[GROUNDING] Verifier API call failed.")
        print(f"[GROUNDING] Error: {error}")

        # Fail closed: unverified questions are not accepted.
        return [
            {
                "grounded": False,
                "reason": "Grounding verification failed."
            }
            for _ in questions
        ]

    result = _parse_json_response(response)

    if result is None:
        return [
            {
                "grounded": False,
                "reason": "Grounding verifier returned invalid JSON."
            }
            for _ in questions
        ]

    results = result.get("results")

    if not isinstance(results, list):
        return [
            {
                "grounded": False,
                "reason": "Grounding verifier returned invalid results."
            }
            for _ in questions
        ]

    verification_map = {}

    for item in results:

        if not isinstance(item, dict):
            continue

        index = item.get("index")

        if not isinstance(index, int):
            continue

        grounded = item.get("grounded")

        if not isinstance(grounded, bool):
            continue

        verification_map[index] = {
            "grounded": grounded,
            "reason": item.get(
                "reason",
                "No reason provided."
            )
        }

    final_results = []

    for index in range(len(questions)):

        verification = verification_map.get(index)

        if verification is None:
            verification = {
                "grounded": False,
                "reason": "Question was not verified."
            }

        final_results.append(verification)

    return final_results