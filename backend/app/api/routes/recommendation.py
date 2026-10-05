from fastapi import APIRouter

from app.services.recommendation_service import get_recommendations


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"]
)


@router.get("/")
def recommendations():
    return get_recommendations()