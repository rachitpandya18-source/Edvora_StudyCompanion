"""
FastAPI route endpoints for Edvora System and AI Configuration Settings.
"""

import os
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services import llm_service

router = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)

_backend_env = Path(__file__).resolve().parent.parent.parent / ".env"


class SettingsStatusResponse(BaseModel):
    gemini_configured: bool
    gemini_primary_model: str
    gemini_fallback_model: str
    api_key_hint: str
    database_connected: bool
    upload_dir: str


class UpdateApiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=15, description="Google Gemini API key")


class TestGeminiResponse(BaseModel):
    success: bool
    message: str
    model_tested: Optional[str] = None


@router.get(
    "",
    response_model=SettingsStatusResponse,
    summary="Get system AI and configuration settings status"
)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    key = llm_service.get_api_key()
    is_configured = llm_service.is_api_key_configured()

    if is_configured and len(key) >= 8:
        hint = f"{key[:4]}...{key[-4:]}"
    elif key:
        hint = "Placeholder / Incomplete"
    else:
        hint = "Not Configured"

    models = llm_service.get_configured_models()
    primary = models[0] if models else "gemini-2.5-flash"
    fallback = models[1] if len(models) > 1 else "gemini-1.5-flash"

    return SettingsStatusResponse(
        gemini_configured=is_configured,
        gemini_primary_model=primary,
        gemini_fallback_model=fallback,
        api_key_hint=hint,
        database_connected=True,
        upload_dir=os.getenv("UPLOAD_DIR", "data/uploads"),
    )


@router.post(
    "/gemini-key",
    summary="Update Google Gemini API key"
)
def update_gemini_key(
    request: UpdateApiKeyRequest,
    current_user: User = Depends(get_current_user),
):
    clean_key = request.api_key.strip()
    if not clean_key or len(clean_key) < 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key must be at least 15 characters long."
        )

    # Set in running process environment
    os.environ["GEMINI_API_KEY"] = clean_key

    # Update .env file persistently
    if _backend_env.exists():
        try:
            content = _backend_env.read_text(encoding="utf-8")
            if re.search(r"^GEMINI_API_KEY=.*$", content, flags=re.MULTILINE):
                updated = re.sub(
                    r"^GEMINI_API_KEY=.*$",
                    f"GEMINI_API_KEY={clean_key}",
                    content,
                    flags=re.MULTILINE
                )
            else:
                updated = content + f"\nGEMINI_API_KEY={clean_key}\n"
            _backend_env.write_text(updated, encoding="utf-8")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist API key to .env: {exc}"
            )

    return {
        "message": "Gemini API key updated successfully.",
        "configured": True,
        "hint": f"{clean_key[:4]}...{clean_key[-4:]}"
    }


@router.post(
    "/test-gemini",
    response_model=TestGeminiResponse,
    summary="Test connectivity with Google Gemini API"
)
def test_gemini_connection(
    current_user: User = Depends(get_current_user),
):
    if not llm_service.is_api_key_configured():
        return TestGeminiResponse(
            success=False,
            message="Gemini API key is not configured or is a placeholder. Please enter a valid key.",
            model_tested=None,
        )

    try:
        models = llm_service.get_configured_models()
        target_model = models[0] if models else "gemini-2.5-flash"
        client = llm_service.get_client()

        response = client.models.generate_content(
            model=target_model,
            contents="Say 'OK' if you can read this."
        )

        return TestGeminiResponse(
            success=True,
            message=f"Gemini API connection successful! ({target_model})",
            model_tested=target_model,
        )
    except Exception as exc:
        err_msg = str(exc)
        if "api key not valid" in err_msg.lower():
            friendly = "Google returned: API key not valid. Please check your API key from Google AI Studio."
        else:
            friendly = f"Connection error: {err_msg}"

        return TestGeminiResponse(
            success=False,
            message=friendly,
            model_tested=None,
        )
