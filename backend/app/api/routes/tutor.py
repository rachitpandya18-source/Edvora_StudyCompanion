from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.document_store import get_document_chunks
from app.services.rag_service import answer_question


router = APIRouter(
    prefix="/tutor",
    tags=["Tutor"]
)


class QuestionRequest(BaseModel):
    question: str
    filename: str


@router.post("/ask")
def ask_question(request: QuestionRequest):

    # Get the uploaded document
    chunks = get_document_chunks(request.filename)

    if chunks is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{request.filename}' not found. Please upload it first."
        )

    # Ask RAG system
    result = answer_question(
        chunks,
        request.question,
        top_k=3
    )

    return result