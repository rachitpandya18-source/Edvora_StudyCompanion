import sys
import os

# Set UTF-8 encoding for Windows stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.pdf_service import extract_pdf_pages
from app.services.chunk_service import chunk_text
from app.services.ingestion_service import ingest_pdf
from app.services.topic_service import extract_topics
from app.services.document_store import store_document, get_document, get_document_chunks
from app.services.retrieval_service import search_chunks
from app.services.rag_service import answer_question
from app.services.quiz_service import generate_quiz
from app.services.quiz_evaluation_service import evaluate_answer
from app.services.learner_model_service import (
    record_answer,
    get_concept_mastery,
    get_topic_mastery,
    get_learner_model,
)
from app.services.recommendation_service import get_recommendations

PDF_FILENAME = "economics rachit(1).pdf"
PDF_PATH = os.path.join("data", "uploads", PDF_FILENAME)

print("=" * 80)
print("PHASE 0 REGRESSION TEST: ECONOMICS STUDY COMPANION")
print("=" * 80)

# 1. Extraction Verification
print("\n[STEP 1] Testing PDF page extraction...")
pages = extract_pdf_pages(PDF_PATH)
print(f"Extracted {len(pages)} pages from {PDF_FILENAME}.")
assert len(pages) == 34, f"Expected 34 pages, got {len(pages)}"
print("✓ Extraction successful: 34 pages verified.")

# 2. Ingestion & Chunks with Page Provenance
print("\n[STEP 2] Ingesting PDF into chunks...")
chunks = ingest_pdf(PDF_PATH, PDF_FILENAME)
print(f"Created {len(chunks)} chunks.")
assert len(chunks) >= 34, "Expected at least 34 chunks"
for i, c in enumerate(chunks[:3]):
    assert "source" in c and c["source"]["filename"] == PDF_FILENAME
    assert "page" in c["source"]
    print(f"  Chunk {i}: ID={c['id']}, Page={c['source']['page']}")
print("✓ Page provenance verified on chunks.")

# 3. Topic & Concept Extraction
print("\n[STEP 3] Extracting Topics & Concepts via LLM...")
topics_data = extract_topics(chunks[:8]) # Test on first 8 chunks for fast/reliable topic extraction
extracted_topics = topics_data.get("topics", [])
print(f"Extracted {len(extracted_topics)} topics:")
for t in extracted_topics:
    print(f"  • {t.get('name')}: {t.get('concepts', [])}")
assert len(extracted_topics) > 0, "Expected at least one topic extracted"
print("✓ Topic extraction successful.")

# Store document in DocumentStore
store_document(PDF_FILENAME, chunks, extracted_topics)
stored = get_document(PDF_FILENAME)
assert stored is not None, "Failed to store document in document store"

# 4. Retrieval Verification
print("\n[STEP 4] Testing Semantic Retrieval on Economics...")
query = "What is the Marginal Principle and when is economic efficiency achieved?"
retrieved = search_chunks(chunks, query, top_k=2)
print(f"Query: '{query}'")
for r in retrieved:
    print(f"  - Page {r['source']['page']} | Score: {r['score']:.4f} | Snippet: {r['text'][:120]}...")
assert any(r['source']['page'] in [6, 7] for r in retrieved), "Expected retrieval of Page 6 or 7 for Marginal Principle"
print("✓ Semantic retrieval correctly retrieved Marginal Principle from Page 6/7.")

# 5. Grounded RAG Tutor Answer & Provenance
print("\n[STEP 5] Testing Grounded Tutor Answer...")
ans_result = answer_question(chunks, query, top_k=2)
print("ANSWER:")
print(ans_result["answer"])
print("SOURCES:")
for s in ans_result["sources"]:
    print(f"  • {s['filename']} - Page {s['page']} (Score: {s['score']:.4f})")
assert len(ans_result["sources"]) > 0, "Expected sources for grounded question"
assert any(s["page"] in [6, 7] for s in ans_result["sources"]), "Expected source page 6 or 7"
print("✓ Grounded tutor answer verified with exact source attribution.")

# 6. Negative Test: Out-of-scope Question (Tutor must NOT hallucinate or falsely cite)
print("\n[STEP 6] Testing Out-of-Scope Question (Tutor Grounding Boundary)...")
unsupported_query = "What is quantum entanglement and how does it affect black hole entropy?"
negative_result = answer_question(chunks, unsupported_query, top_k=2)
print("ANSWER:")
print(negative_result["answer"])
print("SOURCES:", negative_result["sources"])
assert "could not find" in negative_result["answer"].lower() or "not" in negative_result["answer"].lower(), \
    "Tutor should state information is not found in study material"
assert len(negative_result["sources"]) == 0, "Out-of-scope answer should not have attached source citations"
print("✓ Negative test verified: Tutor cleanly rejects unsupported questions with 0 false citations.")

# 7. Grounded Adaptive Quiz Generation & Validation
print("\n[STEP 7] Testing Adaptive Quiz Generation...")
test_topic = "Fundamental Principles of Economics"
test_concept = "Marginal Principle"
quiz_result = generate_quiz(chunks, topic=test_topic, concept=test_concept, num_questions=2)
questions = quiz_result.get("questions", [])
print(f"Generated {len(questions)} quiz questions:")
for i, q in enumerate(questions):
    print(f"\n  Q{i+1}: {q['question']}")
    for opt in q['options']:
        print(f"    - {opt}")
    print(f"    Correct: {q['correct_answer']}")
    print(f"    Difficulty: {q['difficulty']}")
    print(f"    Sources: {q.get('sources')}")
    assert len(q["options"]) == 4, "Question must have 4 options"
    assert q["correct_answer"] in q["options"], "Correct answer must be one of the options"
    assert len(q.get("sources", [])) > 0, "Question must have source citation"
print("✓ Grounded quiz generation and structure verified.")

# 8. Quiz Evaluation & Mastery Tracking (Single Update Exactness)
print("\n[STEP 8] Testing Quiz Evaluation & Mastery Exactness...")
q1 = questions[0]
eval_correct = evaluate_answer(q1, q1["correct_answer"])
assert eval_correct["is_correct"] is True, "Expected correct answer evaluation"

# Record 1 correct answer
res1 = record_answer(test_topic, test_concept, True)
assert res1["correct_answers"] == 1
assert res1["total_questions"] == 1
assert res1["mastery"] == 1.0

# Record 1 incorrect answer
res2 = record_answer(test_topic, test_concept, False)
assert res2["correct_answers"] == 1
assert res2["total_questions"] == 2
assert res2["mastery"] == 0.5

# Verify get_concept_mastery does not increment
m_read = get_concept_mastery(test_topic, test_concept)
assert m_read["total_questions"] == 2, "Read should not increment total_questions"
print("✓ Mastery updates exactly once per response (no phantom increments).")

# 9. Recommendation Generation based on Learner State
print("\n[STEP 9] Testing Recommendations from Learner State...")
# Mark another concept as weak
record_answer(test_topic, "Opportunity Cost", False)
record_answer(test_topic, "Opportunity Cost", False) # 0/2 = 0.0 -> weak
recs = get_recommendations()
print("Recommendations:", recs)
weak_concepts = [w["concept"] for w in recs.get("weak_concepts", [])]
assert "Opportunity Cost" in weak_concepts, "Expected Opportunity Cost in weak concepts"
print("✓ Recommendations accurately reflect the resulting learner state.")

print("\n" + "=" * 80)
print("ALL PHASE 0 VERIFICATION AND REGRESSION TESTS COMPLETED SUCCESSFULLY!")
print("=" * 80)

