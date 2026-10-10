from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.tutor import router as tutor_router
from app.api.routes.document import router as documents_router
from app.api.routes.quiz import router as quiz_router
from app.api.routes.recommendation import router as recommendation_router
from app.api.routes.course import router as course_router
from app.api.routes.curriculum import router as curriculum_router
from app.api.routes.course_tutor import router as course_tutor_router


app = FastAPI(
    title="Personalized AI Study Companion",
    description="AI-powered personalized tutoring and adaptive learning system",
    version="0.1.0"
)


# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routers
app.include_router(course_router)
app.include_router(curriculum_router)
app.include_router(course_tutor_router)
app.include_router(tutor_router)
app.include_router(documents_router)
app.include_router(quiz_router)
app.include_router(recommendation_router)


@app.get("/")
def root():
    return {
        "message": "Personalized AI Study Companion API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}