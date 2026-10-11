"""
Curriculum Generator Service for Edvora (Milestone B11).

Automates extraction and ingestion of grounded academic curriculum graphs
(Topics, Concepts, and Acyclic Prerequisite DAGs) from indexed ContentUnits.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
from collections import deque

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.source import Source
from app.models.content_unit import ContentUnit
from app.models.topic import Topic
from app.models.concept import Concept, ConceptPrerequisite
from app.models.assessment import Question, Assessment, AssessmentAttempt
from app.schemas.curriculum_generator import (
    CurriculumGenerateRequest,
    CurriculumGenerateResponse,
    CurriculumStatusResponse,
    GeneratedTopicItem,
    GeneratedConceptItem,
    GeneratedPrerequisiteItem,
)
from app.services import llm_service

logger = logging.getLogger(__name__)

# Deterministic sampling limits to keep prompt well within LLM context budget
MAX_SAMPLING_CHARS = 16000
MAX_UNITS_PER_SOURCE = 12


# =====================================================================
# Course & Material Verification
# =====================================================================

def verify_course_exists(db: Session, course_id: str) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_id}' not found.",
        )
    return course


# =====================================================================
# Material Sampling Strategy
# =====================================================================

def sample_course_content_units(
    db: Session,
    course_id: str,
    source_ids: Optional[List[str]] = None,
    max_chars: int = MAX_SAMPLING_CHARS,
) -> List[ContentUnit]:
    """
    Selects a bounded, representative set of ContentUnits across course sources.
    Prioritizes:
    - Early units (introductory material, table of contents, syllabus)
    - Stratified, evenly spaced samples across the rest of the document
    Ensures bounded token budget suitable for 100+ page materials.
    """
    query = (
        db.query(ContentUnit)
        .options(joinedload(ContentUnit.source))
        .filter(ContentUnit.course_id == course_id)
    )

    if source_ids:
        # Validate that requested source_ids belong to this course
        invalid_sources = (
            db.query(Source)
            .filter(Source.id.in_(source_ids), Source.course_id != course_id)
            .all()
        )
        if invalid_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source '{invalid_sources[0].id}' does not belong to course '{course_id}'.",
            )
        query = query.filter(ContentUnit.source_id.in_(source_ids))

    all_units = query.order_by(ContentUnit.source_id, ContentUnit.unit_index).all()

    if not all_units:
        return []

    # Group units by source
    units_by_source: Dict[str, List[ContentUnit]] = {}
    for unit in all_units:
        units_by_source.setdefault(unit.source_id, []).append(unit)

    sampled: List[ContentUnit] = []
    total_chars = 0
    num_sources = len(units_by_source)
    chars_per_source = max_chars // max(1, num_sources)

    for s_id, s_units in units_by_source.items():
        source_chars = 0
        s_count = len(s_units)

        if s_count <= 6:
            # Small source: include all units within source character allowance
            chosen_indices = list(range(s_count))
        else:
            # Always pick first 3 units (TOC, intro, preface)
            head_indices = [0, 1, 2]
            # Pick evenly spaced units across remainder
            tail_indices = []
            remaining_slots = min(MAX_UNITS_PER_SOURCE - 3, s_count - 3)
            if remaining_slots > 0:
                step = max(1, (s_count - 3) // remaining_slots)
                tail_indices = list(range(3, s_count, step))[:remaining_slots]
            chosen_indices = head_indices + tail_indices

        for idx in chosen_indices:
            u = s_units[idx]
            u_len = len(u.text or "")
            if source_chars + u_len > chars_per_source and source_chars > 0:
                break
            sampled.append(u)
            source_chars += u_len
            total_chars += u_len
            if total_chars >= max_chars:
                break

        if total_chars >= max_chars:
            break

    return sampled


# =====================================================================
# Prompt Engineering for Structured Curriculum Extraction
# =====================================================================

def build_curriculum_extraction_prompt(
    course_title: str,
    sampled_units: List[ContentUnit],
    max_topics: int = 5,
    concepts_per_topic: int = 4,
    infer_prerequisites: bool = True,
) -> str:
    """
    Constructs a strict educational prompt directing Gemini to output
    a grounded hierarchical curriculum in valid JSON.
    """
    material_excerpts = []
    for idx, u in enumerate(sampled_units, start=1):
        filename = u.source.filename if u.source else "Unknown"
        page = f"Page {u.page_number}" if u.page_number else "N/A"
        clean_text = (u.text or "").strip()
        material_excerpts.append(
            f"--- EXCERPT {idx} [Source: {filename}, {page}] ---\n{clean_text}\n"
        )

    context_str = "\n".join(material_excerpts)

    prereq_instruction = (
        """3. Infer prerequisite relationships between concepts.
   A prerequisite relationship means: "Concept B requires understanding Concept A first."
   Format in "prerequisites": [{"concept": "Concept B", "prerequisite": "Concept A"}].
   CRITICAL: Do NOT create circular dependencies (A requires B and B requires A).
   Prerequisites must represent a valid, forward learning progression."""
        if infer_prerequisites
        else "3. Do not infer prerequisites. Leave the prerequisites array empty: []."
    )

    return f"""You are an expert curriculum designer and academic knowledge graph architect for the course: "{course_title}".

Analyze the study material excerpts below and design an academic curriculum.

==================================================
STUDY MATERIAL EXCERPTS
==================================================
{context_str}

==================================================
DESIGN REQUIREMENTS
==================================================
1. Identify up to {max_topics} distinct academic TOPICS (macro modules or units).
   - Give each topic a clear academic title, a brief educational description, and order_index (0, 1, 2...).
2. Under each topic, identify up to {concepts_per_topic} core CONCEPTS (micro learning objectives).
   - Use concise, precise concept names (e.g., "Binary Search Trees", "Time Complexity", "Opportunity Cost").
   - Provide a 1-2 sentence description explaining the concept.
   - Use order_index (0, 1, 2...) reflecting the order taught within the topic.
   - ONLY include concepts explicitly substantiated by the provided study material.
   - Do NOT invent outside knowledge.
   - Do NOT produce duplicate concept names.
{prereq_instruction}

==================================================
OUTPUT FORMAT
==================================================
Return ONLY valid JSON (no markdown fences, no explanatory text):
{{
  "topics": [
    {{
      "title": "Topic Name",
      "description": "Brief topic description",
      "order_index": 0,
      "concepts": [
        {{
          "name": "Concept Name",
          "description": "Brief concept description",
          "order_index": 0
        }}
      ]
    }}
  ],
  "prerequisites": [
    {{
      "concept": "Advanced Concept Name",
      "prerequisite": "Foundational Concept Name"
    }}
  ]
}}
"""


# =====================================================================
# JSON Parsing & Robust Fallbacks
# =====================================================================

def parse_llm_curriculum_json(raw_text: str) -> Dict[str, Any]:
    """
    Strips code fences and parses JSON safely.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except Exception as exc:
        logger.warning(f"[CURRICULUM_GENERATOR] JSON parsing failed: {exc}. Attempting bracket extraction.")
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
            except Exception:
                raise ValueError("LLM returned malformed JSON that could not be parsed.")
        else:
            raise ValueError("LLM returned non-JSON output.")

    if not isinstance(data, dict):
        raise ValueError("Curriculum payload must be a JSON object with 'topics' and 'prerequisites'.")

    return data


# =====================================================================
# DAG Invariant Validation (Kahn's Algorithm & BFS)
# =====================================================================

def validate_and_sanitize_dag(
    concepts_map: Dict[str, Dict[str, Any]],
    raw_prereq_list: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, str]], bool]:
    """
    Validates proposed prerequisite edges:
    1. Resolves concept names against known concepts (case-insensitive).
    2. Rejects self-prerequisites (A requires A).
    3. Rejects unknown references.
    4. Removes duplicate edges.
    5. Detects cycles using Kahn's topological sort.
       If a cycle is detected, removes the offending back-edges so the returned
       graph is guaranteed strictly acyclic.
    """
    # Key normalization: lower-case name -> canonical concept dict
    name_lookup = {name.lower(): c for name, c in concepts_map.items()}

    valid_edges: List[Tuple[str, str]] = []  # (concept_key, prereq_key)
    seen_edges: Set[Tuple[str, str]] = set()

    for item in raw_prereq_list:
        if not isinstance(item, dict):
            continue
        c_name = str(item.get("concept", "")).strip().lower()
        p_name = str(item.get("prerequisite", "")).strip().lower()

        if not c_name or not p_name:
            continue
        # Self-prerequisite rejection
        if c_name == p_name:
            continue
        # Unknown concept rejection
        if c_name not in name_lookup or p_name not in name_lookup:
            continue

        edge = (c_name, p_name)
        if edge in seen_edges:
            continue
        seen_edges.add(edge)
        valid_edges.append(edge)

    # Topological sorting (Kahn's algorithm) to guarantee zero cycles
    # Edge: (C, P) means C depends on P. Directed dependency arrow: P -> C
    adj: Dict[str, List[str]] = {k: [] for k in name_lookup}
    in_degree: Dict[str, int] = {k: 0 for k in name_lookup}

    sanitized_edges: List[Dict[str, str]] = []

    for c_key, p_key in valid_edges:
        # Check if adding edge p_key -> c_key creates a cycle (i.e. if p_key is already reachable from c_key)
        if _creates_cycle_in_memory(c_key, p_key, adj):
            logger.warning(
                f"[CURRICULUM_GENERATOR] Cycle detected! Dropping back-edge: {c_key} -> {p_key}"
            )
            continue

        adj[p_key].append(c_key)
        in_degree[c_key] = in_degree.get(c_key, 0) + 1
        sanitized_edges.append({
            "concept_name": name_lookup[c_key]["name"],
            "prerequisite_name": name_lookup[p_key]["name"],
        })

    return sanitized_edges, True


def _creates_cycle_in_memory(
    start_node: str,
    target_node: str,
    adj: Dict[str, List[str]],
) -> bool:
    """
    Returns True if target_node is reachable from start_node in adj.
    If target_node is reachable from start_node, then adding an edge from
    target_node to start_node would close a cycle.
    """
    if start_node == target_node:
        return True

    visited = set()
    queue = deque([start_node])

    while queue:
        curr = queue.popleft()
        if curr == target_node:
            return True
        if curr in visited:
            continue
        visited.add(curr)
        for neighbor in adj.get(curr, []):
            if neighbor not in visited:
                queue.append(neighbor)

    return False


# =====================================================================
# Concept-to-Content Grounding
# =====================================================================

def ground_concepts_to_content(
    concepts: List[Dict[str, Any]],
    sampled_units: List[ContentUnit],
) -> None:
    """
    Attaches grounding evidence from sampled ContentUnits to each concept.
    Matches concept keywords/tokens against ContentUnit text.
    """
    for c in concepts:
        c_name_lower = c["name"].lower()
        evidence_list = []

        for u in sampled_units:
            text = (u.text or "")
            text_lower = text.lower()
            if c_name_lower in text_lower:
                # Direct phrase match
                filename = u.source.filename if u.source else "Unknown"
                evidence_list.append({
                    "source_id": u.source_id,
                    "filename": filename,
                    "page_number": u.page_number,
                    "excerpt": text[:180].strip() + ("..." if len(text) > 180 else ""),
                })
                if len(evidence_list) >= 2:
                    break

        if not evidence_list and sampled_units:
            # Fallback: link to the primary unit where related topic occurs
            first_u = sampled_units[0]
            evidence_list.append({
                "source_id": first_u.source_id,
                "filename": first_u.source.filename if first_u.source else "Unknown",
                "page_number": first_u.page_number,
                "excerpt": (first_u.text or "")[:180].strip(),
            })

        c["evidence"] = evidence_list


# =====================================================================
# Main Orchestrator: Generate Curriculum
# =====================================================================

def generate_curriculum(
    db: Session,
    course_id: str,
    request: CurriculumGenerateRequest,
    llm_generator: Optional[Callable[[str], str]] = None,
) -> CurriculumGenerateResponse:
    """
    Generates a validated curriculum graph for a course.
    Supports:
    - 'preview': Runs sampling, LLM extraction, DAG validation, and returns proposed graph WITHOUT persisting.
    - 'replace': Validates safety against existing assessment attempts, atomically deletes previous curriculum,
                 and commits the new Topics, Concepts, and Prerequisite edges.
    """
    # 1. Validate course existence
    course = verify_course_exists(db, course_id)

    # 2. Validate Mode
    mode = request.mode.strip().lower()
    if mode not in ("preview", "replace"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode '{request.mode}'. Supported modes: 'preview' (dry run), 'replace' (persist).",
        )

    # 3. Sample content units (Strict empty-material contract)
    sampled_units = sample_course_content_units(
        db=db,
        course_id=course_id,
        source_ids=request.source_ids,
        max_chars=MAX_SAMPLING_CHARS,
    )

    if not sampled_units:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No indexed course materials available for curriculum extraction.",
        )

    # 4. Generate curriculum structure via LLM
    generator = llm_generator or llm_service.generate_response
    prompt = build_curriculum_extraction_prompt(
        course_title=course.title,
        sampled_units=sampled_units,
        max_topics=request.max_topics,
        concepts_per_topic=request.concepts_per_topic,
        infer_prerequisites=request.infer_prerequisites,
    )

    try:
        raw_llm_response = generator(prompt)
    except Exception as exc:
        logger.error(f"[CURRICULUM_GENERATOR] LLM generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Curriculum generation service is temporarily unavailable. ({exc})",
        )

    # 5. Parse and normalize structured output
    try:
        parsed_data = parse_llm_curriculum_json(raw_llm_response)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to extract structured curriculum: {val_err}",
        )

    raw_topics = parsed_data.get("topics", [])
    raw_prereqs = parsed_data.get("prerequisites", [])

    if not isinstance(raw_topics, list) or not raw_topics:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM did not identify any valid academic topics from the course material.",
        )

    # Normalize topics & concepts, removing duplicates
    structured_topics: List[Dict[str, Any]] = []
    all_concepts_map: Dict[str, Dict[str, Any]] = {}  # lowercase name -> concept dict
    seen_concept_names: Set[str] = set()

    topic_idx = 0
    for t_item in raw_topics[: request.max_topics]:
        if not isinstance(t_item, dict):
            continue
        t_title = str(t_item.get("title", "")).strip()
        if not t_title:
            continue
        t_desc = str(t_item.get("description", "")).strip() or None

        raw_c_list = t_item.get("concepts", [])
        if not isinstance(raw_c_list, list):
            raw_c_list = []

        topic_concepts: List[Dict[str, Any]] = []
        concept_idx = 0

        for c_item in raw_c_list[: request.concepts_per_topic]:
            c_name = ""
            c_desc = None
            if isinstance(c_item, dict):
                c_name = str(c_item.get("name", "")).strip()
                c_desc = str(c_item.get("description", "")).strip() or None
            elif isinstance(c_item, str):
                c_name = c_item.strip()

            if not c_name:
                continue

            c_lower = c_name.lower()
            if c_lower in seen_concept_names:
                # Deduplicate concept across curriculum
                continue

            seen_concept_names.add(c_lower)
            concept_dict = {
                "name": c_name,
                "description": c_desc,
                "order_index": concept_idx,
            }
            topic_concepts.append(concept_dict)
            all_concepts_map[c_lower] = concept_dict
            concept_idx += 1

        if topic_concepts:
            structured_topics.append({
                "title": t_title,
                "description": t_desc,
                "order_index": topic_idx,
                "concepts": topic_concepts,
            })
            topic_idx += 1

    if not structured_topics or not all_concepts_map:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not extract any non-duplicate academic concepts from the material.",
        )

    # 6. Validate DAG and prune cycles
    sanitized_prereqs, is_acyclic = validate_and_sanitize_dag(
        concepts_map=all_concepts_map,
        raw_prereq_list=raw_prereqs if request.infer_prerequisites else [],
    )

    # 7. Ground concepts to content units
    all_concept_list = list(all_concepts_map.values())
    ground_concepts_to_content(all_concept_list, sampled_units)

    # 8. Execution Mode: PREVIEW vs REPLACE
    if mode == "preview":
        preview_topics = [
            GeneratedTopicItem(
                id=f"preview-top-{t['order_index']}",
                title=t["title"],
                description=t["description"],
                order_index=t["order_index"],
                concepts=[
                    GeneratedConceptItem(
                        id=f"preview-con-{c['order_index']}",
                        name=c["name"],
                        description=c["description"],
                        order_index=c["order_index"],
                        evidence=c.get("evidence", []),
                    )
                    for c in t["concepts"]
                ],
            )
            for t in structured_topics
        ]

        preview_prereqs = [
            GeneratedPrerequisiteItem(
                concept_name=p["concept_name"],
                prerequisite_name=p["prerequisite_name"],
            )
            for p in sanitized_prereqs
        ]

        return CurriculumGenerateResponse(
            course_id=course_id,
            mode="preview",
            status="preview",
            topics_count=len(preview_topics),
            concepts_count=len(all_concepts_map),
            prerequisites_count=len(preview_prereqs),
            is_acyclic=is_acyclic,
            topics=preview_topics,
            prerequisites=preview_prereqs,
            message="Curriculum preview generated successfully. Database was not modified.",
        )

    # -----------------------------------------------------------------
    # Mode == "replace": Safe Atomic Database Persistence
    # -----------------------------------------------------------------
    # 8a. Safeguard against deleting curriculum with active student attempts
    existing_concepts = (
        db.query(Concept.id)
        .filter(Concept.course_id == course_id)
        .all()
    )
    if existing_concepts:
        existing_concept_ids = [row[0] for row in existing_concepts]
        # Check if any questions with submitted attempt answers reference these concepts
        attempted_count = (
            db.query(AssessmentAttempt)
            .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
            .filter(Assessment.course_id == course_id, AssessmentAttempt.status == "submitted")
            .count()
        )
        if attempted_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot replace curriculum: course has {attempted_count} completed assessment attempt(s). "
                    "Replacing curriculum would invalidate student assessment history."
                ),
            )

    # 8b. Atomic Transaction Persistence
    try:
        # Delete existing topics (cascades to concepts and prerequisites)
        existing_topics = db.query(Topic).filter(Topic.course_id == course_id).all()
        for et in existing_topics:
            db.delete(et)
        db.flush()

        persisted_topics: List[GeneratedTopicItem] = []
        concept_obj_lookup: Dict[str, Concept] = {}  # lowercase name -> persisted Concept instance

        for t_dict in structured_topics:
            topic_obj = Topic(
                course_id=course_id,
                title=t_dict["title"],
                description=t_dict["description"],
                order_index=t_dict["order_index"],
            )
            db.add(topic_obj)
            db.flush()

            persisted_concepts: List[GeneratedConceptItem] = []
            for c_dict in t_dict["concepts"]:
                concept_obj = Concept(
                    course_id=course_id,
                    topic_id=topic_obj.id,
                    name=c_dict["name"],
                    description=c_dict["description"],
                    order_index=c_dict["order_index"],
                )
                db.add(concept_obj)
                db.flush()

                concept_obj_lookup[c_dict["name"].lower()] = concept_obj

                persisted_concepts.append(
                    GeneratedConceptItem(
                        id=concept_obj.id,
                        name=concept_obj.name,
                        description=concept_obj.description,
                        order_index=concept_obj.order_index,
                        evidence=c_dict.get("evidence", []),
                    )
                )

            persisted_topics.append(
                GeneratedTopicItem(
                    id=topic_obj.id,
                    title=topic_obj.title,
                    description=topic_obj.description,
                    order_index=topic_obj.order_index,
                    concepts=persisted_concepts,
                )
            )

        # Persist prerequisite edges
        persisted_prereqs: List[GeneratedPrerequisiteItem] = []
        for p_dict in sanitized_prereqs:
            c_inst = concept_obj_lookup.get(p_dict["concept_name"].lower())
            p_inst = concept_obj_lookup.get(p_dict["prerequisite_name"].lower())

            if c_inst and p_inst and c_inst.id != p_inst.id:
                edge = ConceptPrerequisite(
                    concept_id=c_inst.id,
                    prerequisite_id=p_inst.id,
                )
                db.add(edge)
                persisted_prereqs.append(
                    GeneratedPrerequisiteItem(
                        concept_name=c_inst.name,
                        prerequisite_name=p_inst.name,
                        concept_id=c_inst.id,
                        prerequisite_id=p_inst.id,
                    )
                )

        db.commit()

        return CurriculumGenerateResponse(
            course_id=course_id,
            mode="replace",
            status="completed",
            topics_count=len(persisted_topics),
            concepts_count=len(concept_obj_lookup),
            prerequisites_count=len(persisted_prereqs),
            is_acyclic=True,
            topics=persisted_topics,
            prerequisites=persisted_prereqs,
            message="Curriculum generated and persisted atomically into course.",
        )

    except Exception as exc:
        db.rollback()
        logger.error(f"[CURRICULUM_GENERATOR] Atomic persistence failed: {exc}", exc_info=True)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist curriculum atomically: {exc}",
        )


# =====================================================================
# Curriculum Status Endpoint
# =====================================================================

def get_curriculum_status(db: Session, course_id: str) -> CurriculumStatusResponse:
    """
    Computes curriculum status metrics dynamically for a course.
    """
    verify_course_exists(db, course_id)

    topic_count = db.query(Topic).filter(Topic.course_id == course_id).count()
    concept_count = db.query(Concept).filter(Concept.course_id == course_id).count()

    edges = (
        db.query(ConceptPrerequisite)
        .join(Concept, ConceptPrerequisite.concept_id == Concept.id)
        .filter(Concept.course_id == course_id)
        .all()
    )
    prereq_count = len(edges)

    # Check acyclicity of persisted edges using Kahn's algorithm
    all_course_concept_ids = [
        row[0] for row in db.query(Concept.id).filter(Concept.course_id == course_id).all()
    ]
    is_acyclic = True
    if prereq_count > 0:
        adj: Dict[str, List[str]] = {c_id: [] for c_id in all_course_concept_ids}
        in_degree: Dict[str, int] = {c_id: 0 for c_id in all_course_concept_ids}
        for e in edges:
            adj[e.prerequisite_id].append(e.concept_id)
            in_degree[e.concept_id] = in_degree.get(e.concept_id, 0) + 1

        queue = deque([node for node, deg in in_degree.items() if deg == 0])
        visited_count = 0
        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        is_acyclic = (visited_count == len(all_course_concept_ids))

    indexed_source_count = (
        db.query(Source)
        .filter(Source.course_id == course_id, Source.processing_status == "completed")
        .count()
    )

    return CurriculumStatusResponse(
        course_id=course_id,
        has_curriculum=(topic_count > 0 and concept_count > 0),
        topic_count=topic_count,
        concept_count=concept_count,
        prerequisite_edge_count=prereq_count,
        is_acyclic=is_acyclic,
        indexed_source_count=indexed_source_count,
    )

