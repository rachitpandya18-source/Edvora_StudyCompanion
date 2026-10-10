"""
FastAPI route endpoints for Curriculum (Topics, Concepts, Prerequisites, and Curriculum Graph).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.curriculum import (
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    TopicListResponse,
    ConceptCreate,
    CourseConceptCreate,
    ConceptUpdate,
    ConceptResponse,
    ConceptDetailResponse,
    ConceptListResponse,
    PrerequisiteCreate,
    PrerequisiteResponse,
    CourseCurriculumResponse,
)
from app.services import curriculum_service

router = APIRouter(
    prefix="/courses",
    tags=["Curriculum"]
)


# =====================================================================
# Topic Endpoints
# =====================================================================

@router.post(
    "/{course_id}/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a topic under a course"
)
def create_topic(
    course_id: str,
    topic_in: TopicCreate,
    db: Session = Depends(get_db)
):
    try:
        topic = curriculum_service.create_topic(
            db=db,
            course_id=course_id,
            title=topic_in.title,
            description=topic_in.description,
            order_index=topic_in.order_index
        )
        return topic
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(val_err).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.get(
    "/{course_id}/topics",
    response_model=TopicListResponse,
    summary="List topics for a course"
)
def list_topics(
    course_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    try:
        topics, total = curriculum_service.get_topics(
            db=db,
            course_id=course_id,
            skip=skip,
            limit=limit
        )
        return TopicListResponse(items=topics, total=total)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.get(
    "/{course_id}/topics/{topic_id}",
    response_model=TopicResponse,
    summary="Get a specific topic"
)
def get_topic(
    course_id: str,
    topic_id: str,
    db: Session = Depends(get_db)
):
    try:
        topic = curriculum_service.get_topic(db=db, course_id=course_id, topic_id=topic_id)
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{topic_id}' not found in course '{course_id}'."
            )
        return topic
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.put(
    "/{course_id}/topics/{topic_id}",
    response_model=TopicResponse,
    summary="Update a topic"
)
def update_topic(
    course_id: str,
    topic_id: str,
    topic_in: TopicUpdate,
    db: Session = Depends(get_db)
):
    try:
        return curriculum_service.update_topic(
            db=db,
            course_id=course_id,
            topic_id=topic_id,
            title=topic_in.title,
            description=topic_in.description,
            order_index=topic_in.order_index
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(val_err).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.delete(
    "/{course_id}/topics/{topic_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a topic and its associated concepts"
)
def delete_topic(
    course_id: str,
    topic_id: str,
    db: Session = Depends(get_db)
):
    try:
        curriculum_service.delete_topic(db=db, course_id=course_id, topic_id=topic_id)
        return {
            "message": f"Topic '{topic_id}' and all associated concepts deleted successfully.",
            "topic_id": topic_id,
            "course_id": course_id
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


# =====================================================================
# Concept Endpoints
# =====================================================================

@router.post(
    "/{course_id}/topics/{topic_id}/concepts",
    response_model=ConceptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a concept under a specific topic"
)
def create_concept_under_topic(
    course_id: str,
    topic_id: str,
    concept_in: ConceptCreate,
    db: Session = Depends(get_db)
):
    try:
        return curriculum_service.create_concept(
            db=db,
            course_id=course_id,
            topic_id=topic_id,
            name=concept_in.name,
            description=concept_in.description,
            order_index=concept_in.order_index
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(val_err).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.post(
    "/{course_id}/concepts",
    response_model=ConceptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a concept in a course specifying topic_id in body"
)
def create_concept(
    course_id: str,
    concept_in: CourseConceptCreate,
    db: Session = Depends(get_db)
):
    try:
        return curriculum_service.create_concept(
            db=db,
            course_id=course_id,
            topic_id=concept_in.topic_id,
            name=concept_in.name,
            description=concept_in.description,
            order_index=concept_in.order_index
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(val_err).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.get(
    "/{course_id}/topics/{topic_id}/concepts",
    response_model=ConceptListResponse,
    summary="List concepts under a topic"
)
def list_concepts_under_topic(
    course_id: str,
    topic_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    try:
        concepts, total = curriculum_service.get_concepts(
            db=db,
            course_id=course_id,
            topic_id=topic_id,
            skip=skip,
            limit=limit
        )
        return ConceptListResponse(items=concepts, total=total)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.get(
    "/{course_id}/concepts",
    response_model=ConceptListResponse,
    summary="List all concepts in a course"
)
def list_course_concepts(
    course_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    try:
        concepts, total = curriculum_service.get_concepts(
            db=db,
            course_id=course_id,
            topic_id=None,
            skip=skip,
            limit=limit
        )
        return ConceptListResponse(items=concepts, total=total)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.get(
    "/{course_id}/concepts/{concept_id}",
    response_model=ConceptDetailResponse,
    summary="Get a concept by ID with prerequisite IDs"
)
def get_concept(
    course_id: str,
    concept_id: str,
    db: Session = Depends(get_db)
):
    try:
        concept = curriculum_service.get_concept(db=db, course_id=course_id, concept_id=concept_id)
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{concept_id}' not found in course '{course_id}'."
            )
        prereq_ids = [p.id for p in concept.prerequisites]
        return ConceptDetailResponse(
            id=concept.id,
            course_id=concept.course_id,
            topic_id=concept.topic_id,
            name=concept.name,
            description=concept.description,
            order_index=concept.order_index,
            created_at=concept.created_at,
            updated_at=concept.updated_at,
            prerequisite_ids=prereq_ids
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.put(
    "/{course_id}/concepts/{concept_id}",
    response_model=ConceptResponse,
    summary="Update a concept"
)
def update_concept(
    course_id: str,
    concept_id: str,
    concept_in: ConceptUpdate,
    db: Session = Depends(get_db)
):
    try:
        return curriculum_service.update_concept(
            db=db,
            course_id=course_id,
            concept_id=concept_id,
            name=concept_in.name,
            description=concept_in.description,
            order_index=concept_in.order_index,
            topic_id=concept_in.topic_id
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(val_err).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.delete(
    "/{course_id}/concepts/{concept_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a concept and cascade clean its prerequisite edges"
)
def delete_concept(
    course_id: str,
    concept_id: str,
    db: Session = Depends(get_db)
):
    try:
        curriculum_service.delete_concept(db=db, course_id=course_id, concept_id=concept_id)
        return {
            "message": f"Concept '{concept_id}' deleted successfully.",
            "concept_id": concept_id,
            "course_id": course_id
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


# =====================================================================
# Prerequisite Endpoints
# =====================================================================

@router.post(
    "/{course_id}/concepts/{concept_id}/prerequisites",
    response_model=PrerequisiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a prerequisite to a concept"
)
def add_prerequisite(
    course_id: str,
    concept_id: str,
    prereq_in: PrerequisiteCreate,
    db: Session = Depends(get_db)
):
    try:
        edge = curriculum_service.add_prerequisite(
            db=db,
            course_id=course_id,
            concept_id=concept_id,
            prerequisite_id=prereq_in.prerequisite_id
        )
        return edge
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        if "already a prerequisite" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.get(
    "/{course_id}/concepts/{concept_id}/prerequisites",
    response_model=List[ConceptResponse],
    summary="List all prerequisite concepts for a given concept"
)
def get_prerequisites(
    course_id: str,
    concept_id: str,
    db: Session = Depends(get_db)
):
    try:
        return curriculum_service.get_prerequisites(
            db=db,
            course_id=course_id,
            concept_id=concept_id
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.delete(
    "/{course_id}/concepts/{concept_id}/prerequisites/{prerequisite_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a prerequisite relationship from a concept"
)
def remove_prerequisite(
    course_id: str,
    concept_id: str,
    prerequisite_id: str,
    db: Session = Depends(get_db)
):
    try:
        curriculum_service.remove_prerequisite(
            db=db,
            course_id=course_id,
            concept_id=concept_id,
            prerequisite_id=prerequisite_id
        )
        return {
            "message": f"Prerequisite '{prerequisite_id}' removed from concept '{concept_id}'.",
            "concept_id": concept_id,
            "prerequisite_id": prerequisite_id,
            "course_id": course_id
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


# =====================================================================
# Full Curriculum Graph / Overview Endpoint
# =====================================================================

@router.get(
    "/{course_id}/curriculum",
    response_model=CourseCurriculumResponse,
    summary="Get the complete curriculum graph for a course"
)
def get_course_curriculum(
    course_id: str,
    db: Session = Depends(get_db)
):
    try:
        return curriculum_service.get_course_curriculum(db=db, course_id=course_id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )

