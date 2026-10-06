from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.document_store import get_document_chunks
from app.services.quiz_service import generate_quiz
from app.services.quiz_evaluation_service import evaluate_answer
from app.services.learner_model_service import get_concept_mastery
from app.services.learner_model_service import (
    record_answer,
    get_concept_mastery
)

router = APIRouter(
    prefix="/quiz",
    tags=["Quiz"]
)


class QuizRequest(BaseModel):
    filename: str
    topic: str
    concept: str
    num_questions: int = 5


@router.post("/generate")
def generate_quiz_endpoint(request: QuizRequest):

    # --------------------------------------------------
    # 1. Get uploaded document
    # --------------------------------------------------

    chunks = get_document_chunks(
        request.filename
    )

    if chunks is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Document '{request.filename}' "
                "not found. Please upload it first."
            )
        )

    # --------------------------------------------------
    # 2. Validate number of questions
    # --------------------------------------------------

    if request.num_questions < 1:
        raise HTTPException(
            status_code=400,
            detail="num_questions must be at least 1."
        )

    if request.num_questions > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 questions are allowed."
        )

    # --------------------------------------------------
    # 3. Generate quiz
    # --------------------------------------------------

    try:

        result = generate_quiz(
            chunks=chunks,
            topic=request.topic,
            concept=request.concept,
            num_questions=request.num_questions
        )

        return {
            "filename": request.filename,
            "topic": request.topic,
            "concept": request.concept,
            "questions": result.get(
                "questions",
                []
            )
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
class QuizEvaluationRequest(BaseModel):
    question: dict
    selected_answer: str


@router.post("/evaluate")
def evaluate_quiz_answer(request: QuizEvaluationRequest):

    try:
        result = evaluate_answer(
            request.question,
            request.selected_answer
        )

        return result

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
class QuizSubmitRequest(BaseModel):
    topic: str
    concept: str
    questions: list[dict]
    selected_answers: dict


@router.post("/submit")
def submit_quiz(request: QuizSubmitRequest):

    if not request.questions:
        raise HTTPException(
            status_code=400,
            detail="No quiz questions were provided."
        )

    results = []
    correct_count = 0

    for index, question in enumerate(request.questions):

        selected_answer = request.selected_answers.get(
            str(index)
        )

        if not selected_answer:
            results.append({
                "question_index": index,
                "is_correct": False,
                "selected_answer": None,
                "correct_answer": question.get(
                    "correct_answer"
                ),
                "explanation": question.get(
                    "explanation",
                    ""
                ),
                "sources": question.get(
                    "sources",
                    []
                )
            })

            record_answer(
                request.topic,
                request.concept,
                False
            )

            continue

        evaluation = evaluate_answer(
            question,
            selected_answer
        )

        is_correct = evaluation["is_correct"]

        if is_correct:
            correct_count += 1

        record_answer(
            request.topic,
            request.concept,
            is_correct
        )

        results.append({
            "question_index": index,
            **evaluation
        })

    total_questions = len(request.questions)

    mastery = correct_count / total_questions

    mastery_data = {
        "score": correct_count,
        "total": total_questions,
        "quiz_mastery": round(mastery, 2)
    }

    return {
        "topic": request.topic,
        "concept": request.concept,
        "results": results,
        "score": correct_count,
        "total": total_questions,
        "quiz_mastery": round(mastery, 2),
        "learner_mastery": get_concept_mastery(
            request.topic,
            request.concept
        )
    }