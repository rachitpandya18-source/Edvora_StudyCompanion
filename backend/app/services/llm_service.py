import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)


# Models are kept here so we can easily change them later.
MODELS = [
    os.getenv("GEMINI_PRIMARY_MODEL"),
    os.getenv("GEMINI_FALLBACK_MODEL"),
]

MODELS = [model for model in MODELS if model]


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

    if not MODELS:
        raise ValueError("No Gemini models configured in .env")

    last_error = None

    for index, model in enumerate(MODELS):

        try:
            print(f"[LLM] Trying model: {model}")

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            print(f"[LLM] Success: {model}")

            return response.text

        except Exception as error:

            last_error = error

            print(f"[LLM] Model failed: {model}")
            print(f"[LLM] Error: {error}")

            if is_retryable_error(error):
                print("[LLM] Temporary error detected.")

                if index < len(MODELS) - 1:
                    print("[LLM] Switching to fallback model...")
                    time.sleep(1)
                    continue

            # Don't hide permanent errors.
            raise error

    raise RuntimeError(
        f"All configured Gemini models failed. Last error: {last_error}"
    )