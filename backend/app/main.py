import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.tutor import router as tutor_router
from app.api.routes.document import router as documents_router
from app.api.routes.quiz import router as quiz_router
from app.api.routes.recommendation import router as recommendation_router
from app.api.routes.course import router as course_router
from app.api.routes.curriculum import router as curriculum_router
from app.api.routes.course_tutor import router as course_tutor_router
from app.api.routes.assessment import router as assessment_router
from app.api.routes.learner_mastery import router as learner_mastery_router
from app.api.routes.study_planner import router as study_planner_router
from app.api.routes.practice import router as practice_router
from app.api.routes.analytics import router as analytics_router


from contextlib import asynccontextmanager
from app.core.security import validate_jwt_secret_for_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_jwt_secret_for_startup()
    yield


app = FastAPI(
    title="Personalized AI Study Companion",
    description="AI-powered personalized tutoring and adaptive learning system",
    version="0.1.0",
    lifespan=lifespan,
)


# Allow frontend to communicate with backend
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
if not allowed_origins:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routers
app.include_router(auth_router)
app.include_router(course_router)
app.include_router(curriculum_router)
app.include_router(course_tutor_router)
app.include_router(assessment_router)
app.include_router(learner_mastery_router)
app.include_router(study_planner_router)
app.include_router(practice_router)
app.include_router(analytics_router)
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