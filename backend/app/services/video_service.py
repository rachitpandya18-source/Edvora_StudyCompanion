"""
Video Ingestion Service for Edvora Study Companion.

Handles lecture video recordings (.mp4, .mov, .m4v, .webm):
- Extracts companion transcripts (.vtt, .srt, .txt) if present
- Generates structured, indexed content units for video materials
- Preserves video file metadata and playback provenance
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def parse_vtt_or_srt(transcript_path: Path) -> List[Dict[str, Any]]:
    """Parses a WebVTT or SubRip (.srt) subtitle file into timestamped segments."""
    try:
        content = transcript_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning(f"[VIDEO_SERVICE] Failed to read subtitle file {transcript_path}: {exc}")
        return []

    # Clean header tags
    lines = content.splitlines()
    segments = []
    current_timestamp = None
    current_lines = []
    page_num = 1

    time_pattern = re.compile(r"(\d{2}:\d{2}(?::\d{2})?(?:[.,]\d{3})?)\s*-->\s*(\d{2}:\d{2}(?::\d{2})?(?:[.,]\d{3})?)")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or line.isdigit():
            continue
        match = time_pattern.search(line)
        if match:
            if current_lines:
                text = " ".join(current_lines).strip()
                if text:
                    segments.append({
                        "page_number": page_num,
                        "text": f"[{current_timestamp or '00:00'}] {text}"
                    })
                    page_num += 1
                current_lines = []
            current_timestamp = match.group(1)
        else:
            current_lines.append(line)

    if current_lines:
        text = " ".join(current_lines).strip()
        if text:
            segments.append({
                "page_number": page_num,
                "text": f"[{current_timestamp or '00:00'}] {text}"
            })

    return segments


def extract_video_content(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """
    Extracts educational content units from a video file:
    1. Looks for an adjacent transcript or subtitle file (e.g. video.vtt, video.srt, video.txt).
    2. If found, parses timed speech into structured units.
    3. If no transcript file is found, creates an indexed overview unit capturing the
       lecture video title, format, and study metadata.
    """
    v_path = Path(file_path)
    stem = v_path.stem
    parent = v_path.parent

    # Check for possible companion transcript files
    for ext in [".vtt", ".srt", ".txt", ".transcript.txt"]:
        companion = parent / f"{stem}{ext}"
        if companion.exists():
            segments = parse_vtt_or_srt(companion)
            if segments:
                logger.info(f"[VIDEO_SERVICE] Found companion transcript: {companion.name}")
                return segments

    # Format file size for metadata
    try:
        size_bytes = v_path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)
    except Exception:
        size_mb = 0

    clean_name = stem.replace("_", " ").replace("-", " ").title()

    overview_text = (
        f"Lecture Recording: {clean_name}\n"
        f"File: {filename} ({size_mb} MB)\n"
        f"Indexed course lecture recording. Students can review and reference this recording in course materials."
    )

    return [
        {
            "page_number": 1,
            "text": overview_text
        }
    ]
