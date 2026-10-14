import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai

_backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
if _backend_env.exists():
    load_dotenv(_backend_env)
else:
    load_dotenv()

def get_api_key() -> str:
    if _backend_env.exists():
        load_dotenv(_backend_env, override=False)
    return os.getenv("GEMINI_API_KEY", "").strip()


def is_api_key_configured() -> bool:
    key = get_api_key()
    if not key:
        return False
    lower = key.lower()
    placeholders = ["your_gemini_api_key", "placeholder", "test_key", "change_me", "example"]
    if any(p in lower for p in placeholders):
        return False
    return len(key) >= 15


_cached_client = None
_cached_key = None


def get_client():
    global _cached_client, _cached_key
    current_key = get_api_key()
    if not current_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    if _cached_client is None or _cached_key != current_key:
        _cached_client = genai.Client(api_key=current_key)
        _cached_key = current_key
    return _cached_client


def get_configured_models():
    primary = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-2.0-flash").strip()
    fallback = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-flash").strip()
    candidates = [primary, fallback, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]
    models = []
    for m in candidates:
        if m and m not in models:
            models.append(m)
    return models


# Keep backward-compatible module attributes
API_KEY = get_api_key()
try:
    client = get_client() if API_KEY else None
except Exception:
    client = None
MODELS = get_configured_models()


def is_retryable_error(error):
    """
    Returns True when the error is temporary and
    we should try another model.
    """
    error_text = str(error).lower()
    retryable_errors = [
        "503",
        "unavailable",
        "429",
        "resource_exhausted",
        "rate limit",
        "timeout",
        "timed out",
        "deadline exceeded",
        "internal",
    ]
    return any(error_type in error_text for error_type in retryable_errors)


def generate_response(prompt: str):
    """
    Try the configured Gemini models one by one.
    If the primary model fails with a temporary error,
    automatically move to the fallback model.
    """
    if not is_api_key_configured():
        raise RuntimeError(
            "Google Gemini API key is not configured or is a placeholder. "
            "Please configure a valid GEMINI_API_KEY in backend/.env or under Settings."
        )

    client_instance = get_client()
    models = get_configured_models()

    if not models:
        raise ValueError("No Gemini models configured in .env")

    last_error = None

    for index, model in enumerate(models):
        try:
            print(f"[LLM] Trying model: {model}")
            response = client_instance.models.generate_content(
                model=model,
                contents=prompt
            )
            print(f"[LLM] Success: {model}")
            return response.text

        except Exception as error:
            last_error = error
            err_msg = str(error)
            print(f"[LLM] Model failed: {model}")
            print(f"[LLM] Error: {error}")

            if "api key not valid" in err_msg.lower() or "invalid api key" in err_msg.lower():
                raise RuntimeError(
                    "Google Gemini API key is invalid. Please verify your GEMINI_API_KEY in backend/.env or under Settings."
                ) from error

            if is_retryable_error(error):
                print("[LLM] Temporary error detected.")
                if index < len(models) - 1:
                    print("[LLM] Switching to fallback model...")
                    time.sleep(1)
                    continue

            # Don't hide permanent errors.
            raise error

    raise RuntimeError(
        f"All configured Gemini models failed. Last error: {last_error}"
    )