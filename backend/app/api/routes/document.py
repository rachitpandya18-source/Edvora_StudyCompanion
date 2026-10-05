from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil

from app.services.ingestion_service import ingest_pdf
from app.services.topic_service import extract_topics
from app.services.document_store import store_document

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
def upload_document(file: UploadFile = File(...)):

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    file_path = UPLOAD_DIR / file.filename

    # Save uploaded PDF
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text and create chunks
    chunks = ingest_pdf(
        str(file_path),
        file.filename
    )

    # Extract topics and concepts
    topics_result = extract_topics(chunks)

    topics = topics_result.get("topics", [])

    # Store chunks + topics
    store_document(
        file.filename,
        chunks,
        topics
    )

    return {
        "message": "PDF uploaded and processed successfully",
        "filename": file.filename,
        "path": str(file_path),
        "chunks_created": len(chunks),
        "topics_created": len(topics),
        "topics": topics
    }