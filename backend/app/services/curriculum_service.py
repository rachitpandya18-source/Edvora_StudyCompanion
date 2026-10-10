"""
Curriculum service for Edvora.

Manages persistent Topics, Concepts, and the directed acyclic graph (DAG)
of Concept Prerequisites scoped to a Course.
"""

from typing import List, Optional, Tuple, Dict, Any, Set
from collections import deque
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.topic import Topic
from app.models.concept import Concept, ConceptPrerequisite


# =====================================================================
# Course Verification Helper
# =====================================================================

def verify_course_exists(db: Session, course_id: str) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError(f"Course '{course_id}' not found.")
    return course


# =====================================================================
# Topic Operations
# =====================================================================

def create_topic(
    db: Session,
    course_id: str,
    title: str,
    description: Optional[str] = None,
    order_index: int = 0
) -> Topic:
    verify_course_exists(db, course_id)
    topic = Topic(
        course_id=course_id,
        title=title,
        description=description,
        order_index=order_index
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


def get_topics(
    db: Session,
    course_id: str,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Topic], int]:
    verify_course_exists(db, course_id)
    query = (
        db.query(Topic)
        .filter(Topic.course_id == course_id)
        .order_by(Topic.order_index, Topic.created_at)
    )
    total = query.count()
    topics = query.offset(skip).limit(limit).all()
    return topics, total


def get_topic(db: Session, course_id: str, topic_id: str) -> Optional[Topic]:
    verify_course_exists(db, course_id)
    return db.query(Topic).filter(
        Topic.id == topic_id,
        Topic.course_id == course_id
    ).first()


def update_topic(
    db: Session,
    course_id: str,
    topic_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    order_index: Optional[int] = None
) -> Topic:
    topic = get_topic(db, course_id, topic_id)
    if not topic:
        raise ValueError(f"Topic '{topic_id}' not found in course '{course_id}'.")

    if title is not None:
        topic.title = title
    if description is not None:
        topic.description = description
    if order_index is not None:
        topic.order_index = order_index

    db.commit()
    db.refresh(topic)
    return topic


def delete_topic(db: Session, course_id: str, topic_id: str) -> None:
    topic = get_topic(db, course_id, topic_id)
    if not topic:
        raise ValueError(f"Topic '{topic_id}' not found in course '{course_id}'.")

    db.delete(topic)
    db.commit()


# =====================================================================
# Concept Operations
# =====================================================================

def create_concept(
    db: Session,
    course_id: str,
    topic_id: str,
    name: str,
    description: Optional[str] = None,
    order_index: int = 0
) -> Concept:
    verify_course_exists(db, course_id)

    # Validate parent topic belongs to this course
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise ValueError(f"Topic '{topic_id}' not found.")
    if topic.course_id != course_id:
        raise ValueError(
            f"Topic '{topic_id}' belongs to course '{topic.course_id}', "
            f"not target course '{course_id}'."
        )

    concept = Concept(
        course_id=course_id,
        topic_id=topic_id,
        name=name,
        description=description,
        order_index=order_index
    )
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def get_concepts(
    db: Session,
    course_id: str,
    topic_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Concept], int]:
    verify_course_exists(db, course_id)
    query = db.query(Concept).filter(Concept.course_id == course_id)
    if topic_id:
        # Validate topic belongs to this course
        topic = get_topic(db, course_id, topic_id)
        if not topic:
            raise ValueError(f"Topic '{topic_id}' not found in course '{course_id}'.")
        query = query.filter(Concept.topic_id == topic_id)

    query = query.order_by(Concept.order_index, Concept.created_at)
    total = query.count()
    concepts = query.offset(skip).limit(limit).all()
    return concepts, total


def get_concept(db: Session, course_id: str, concept_id: str) -> Optional[Concept]:
    verify_course_exists(db, course_id)
    return db.query(Concept).filter(
        Concept.id == concept_id,
        Concept.course_id == course_id
    ).first()


def update_concept(
    db: Session,
    course_id: str,
    concept_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    order_index: Optional[int] = None,
    topic_id: Optional[str] = None
) -> Concept:
    concept = get_concept(db, course_id, concept_id)
    if not concept:
        raise ValueError(f"Concept '{concept_id}' not found in course '{course_id}'.")

    if topic_id is not None:
        # Ensure new topic exists and belongs to the same course
        new_topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not new_topic:
            raise ValueError(f"Target topic '{topic_id}' not found.")
        if new_topic.course_id != course_id:
            raise ValueError(
                f"Cannot move concept to topic '{topic_id}' in course '{new_topic.course_id}'. "
                f"Target topic must belong to course '{course_id}'."
            )
        concept.topic_id = topic_id

    if name is not None:
        concept.name = name
    if description is not None:
        concept.description = description
    if order_index is not None:
        concept.order_index = order_index

    db.commit()
    db.refresh(concept)
    return concept


def delete_concept(db: Session, course_id: str, concept_id: str) -> None:
    concept = get_concept(db, course_id, concept_id)
    if not concept:
        raise ValueError(f"Concept '{concept_id}' not found in course '{course_id}'.")

    db.delete(concept)
    db.commit()


# =====================================================================
# Prerequisite Graph & Cycle Detection
# =====================================================================

def has_prerequisite_cycle(
    db: Session,
    start_concept_id: str,
    target_concept_id: str
) -> bool:
    """
    Check if target_concept_id can be reached by following prerequisites starting from start_concept_id.

    If target_concept_id is reachable from start_concept_id via prerequisites,
    then adding an edge where target_concept_id requires start_concept_id would close a cycle.

    Uses Breadth-First Search (BFS) over ConceptPrerequisite edges.
    """
    if start_concept_id == target_concept_id:
        return True

    visited: Set[str] = set()
    queue = deque([start_concept_id])

    while queue:
        curr = queue.popleft()
        if curr in visited:
            continue
        visited.add(curr)

        # Retrieve all prerequisites that 'curr' depends on
        prereq_ids = [
            row[0] for row in db.query(ConceptPrerequisite.prerequisite_id)
            .filter(ConceptPrerequisite.concept_id == curr)
            .all()
        ]

        for p_id in prereq_ids:
            if p_id == target_concept_id:
                return True
            if p_id not in visited:
                queue.append(p_id)

    return False


def add_prerequisite(
    db: Session,
    course_id: str,
    concept_id: str,
    prerequisite_id: str
) -> ConceptPrerequisite:
    """
    Add a directed prerequisite relationship: concept_id requires prerequisite_id.

    Validations:
    1. Rejects self-prerequisites (concept_id == prerequisite_id).
    2. Validates concept exists in course_id.
    3. Validates prerequisite exists and belongs to the exact same course (cross-course rejection).
    4. Rejects duplicate prerequisite edges.
    5. Rejects direct and indirect cycles to preserve DAG invariant.
    """
    # 1. Reject self-prerequisite
    if concept_id == prerequisite_id:
        raise ValueError("A concept cannot be a prerequisite of itself.")

    # 2. Verify target concept exists in course
    concept = db.query(Concept).filter(
        Concept.id == concept_id,
        Concept.course_id == course_id
    ).first()
    if not concept:
        raise ValueError(f"Concept '{concept_id}' not found in course '{course_id}'.")

    # 3. Verify prerequisite concept exists in course (and check for cross-course error clarity)
    prereq = db.query(Concept).filter(
        Concept.id == prerequisite_id,
        Concept.course_id == course_id
    ).first()
    if not prereq:
        other_course_concept = db.query(Concept).filter(Concept.id == prerequisite_id).first()
        if other_course_concept:
            raise ValueError(
                f"Prerequisite concept '{prerequisite_id}' belongs to a different course "
                f"('{other_course_concept.course_id}') than concept '{concept_id}' ('{course_id}')."
            )
        raise ValueError(f"Prerequisite concept '{prerequisite_id}' not found.")

    # 4. Check for duplicate relationship
    existing = db.query(ConceptPrerequisite).filter(
        ConceptPrerequisite.concept_id == concept_id,
        ConceptPrerequisite.prerequisite_id == prerequisite_id
    ).first()
    if existing:
        raise ValueError(
            f"Concept '{prerequisite_id}' is already a prerequisite of concept '{concept_id}'."
        )

    # 5. Check for direct and indirect cycles
    if has_prerequisite_cycle(db, start_concept_id=prerequisite_id, target_concept_id=concept_id):
        raise ValueError(
            f"Cannot add prerequisite: relationship would create a cycle (direct or indirect) "
            f"between '{concept_id}' and '{prerequisite_id}'."
        )

    # 6. Create relationship edge
    edge = ConceptPrerequisite(
        concept_id=concept_id,
        prerequisite_id=prerequisite_id
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def remove_prerequisite(
    db: Session,
    course_id: str,
    concept_id: str,
    prerequisite_id: str
) -> None:
    # Verify concepts exist in this course
    concept = get_concept(db, course_id, concept_id)
    if not concept:
        raise ValueError(f"Concept '{concept_id}' not found in course '{course_id}'.")

    edge = db.query(ConceptPrerequisite).filter(
        ConceptPrerequisite.concept_id == concept_id,
        ConceptPrerequisite.prerequisite_id == prerequisite_id
    ).first()

    if not edge:
        raise ValueError(
            f"Prerequisite relationship from '{prerequisite_id}' to '{concept_id}' not found."
        )

    db.delete(edge)
    db.commit()


def get_prerequisites(
    db: Session,
    course_id: str,
    concept_id: str
) -> List[Concept]:
    concept = get_concept(db, course_id, concept_id)
    if not concept:
        raise ValueError(f"Concept '{concept_id}' not found in course '{course_id}'.")

    return concept.prerequisites


# =====================================================================
# Full Course Curriculum Structure Overview
# =====================================================================

def get_course_curriculum(
    db: Session,
    course_id: str
) -> Dict[str, Any]:
    verify_course_exists(db, course_id)

    # 1. Fetch topics with eager concepts
    topics = (
        db.query(Topic)
        .options(joinedload(Topic.concepts))
        .filter(Topic.course_id == course_id)
        .order_by(Topic.order_index, Topic.created_at)
        .all()
    )

    # 2. Fetch all prerequisite edges between concepts in this course
    edges = (
        db.query(ConceptPrerequisite)
        .join(Concept, ConceptPrerequisite.concept_id == Concept.id)
        .filter(Concept.course_id == course_id)
        .all()
    )

    edge_list = [
        {"concept_id": e.concept_id, "prerequisite_id": e.prerequisite_id}
        for e in edges
    ]

    return {
        "course_id": course_id,
        "topics": topics,
        "prerequisites": edge_list
    }

