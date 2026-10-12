import os
import json
import base64
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Target PBKDF2 iterations adhering to NIST SP 800-63B and OWASP 2023 recommendations
PBKDF2_ROUNDS = 600_000
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # Default 24h

# Blocklist of prohibited default or trivial secrets
INSECURE_SECRETS = {
    "edvora-secure-jwt-secret-key-2026-production",
    "edvora-production-secret-key-change-in-prod",
    "secret",
    "jwt-secret",
    "changeme",
    "password",
    "default",
}


def is_unauthenticated_fallback_allowed() -> bool:
    """
    Fail-closed environment check.
    Authentication is strictly required by default.
    Only explicit, normalized values in ('test', 'testing', 'development') allow fallback.
    Missing, unknown, or production values (e.g., 'production', 'prod', 'staging')
    strictly fail-closed and enforce JWT authentication.
    """
    raw_env = os.getenv("ENVIRONMENT")
    if not raw_env:
        return False
    normalized = raw_env.strip().lower()
    return normalized in {"test", "testing", "development"}


def get_jwt_secret_key() -> str:
    """
    Retrieve and validate the JWT secret key.
    Fails closed in production if missing, too short (<32 chars), or matching known defaults.
    """
    secret = os.getenv("JWT_SECRET_KEY")
    if secret:
        secret = secret.strip()

    if not is_unauthenticated_fallback_allowed():
        if not secret:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: JWT_SECRET_KEY environment variable is missing. "
                "Production startup aborted. You must set a dedicated, cryptographically strong secret."
            )
        if secret.lower() in INSECURE_SECRETS or len(secret) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Insecure or default JWT_SECRET_KEY detected. "
                "Production startup aborted. Must be at least 32 characters and not use default credentials."
            )
        return secret

    # Non-production fallback secret for tests and local development only
    return secret or "test-secret-key-for-development-and-testing-only-32chars"


def validate_jwt_secret_for_startup() -> None:
    """
    Validates JWT_SECRET_KEY configuration at application startup.
    Fails startup immediately if running in production without a valid secret.
    """
    get_jwt_secret_key()


def _base64url_encode(data: bytes) -> str:
    """Encode bytes to standard RFC 7519 URL-safe base64 string without trailing '=' padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(encoded_str: str) -> bytes:
    """Decode an RFC 7519 URL-safe base64 string, restoring required padding."""
    rem = len(encoded_str) % 4
    if rem > 0:
        encoded_str += "=" * (4 - rem)
    return base64.urlsafe_b64decode(encoded_str.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with 600,000 rounds and a 16-byte random salt.
    Format: pbkdf2:sha256:600000$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ROUNDS
    )
    return f"pbkdf2:sha256:{PBKDF2_ROUNDS}${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an existing PBKDF2 hash using timing-safe comparison.
    Reads work factor dynamically from header to support legacy hashes with fewer rounds.
    """
    if not hashed_password or "$" not in hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        header, salt, original_hash = parts
        _, _, rounds_str = header.split(":")
        rounds = int(rounds_str)

        computed = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            rounds
        ).hex()

        return hmac.compare_digest(computed, original_hash)
    except Exception:
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    """
    Returns True if the stored hash uses fewer iterations than the current target (600,000).
    Allows transparent rehashing on successful user login.
    """
    if not hashed_password or "$" not in hashed_password:
        return True
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return True
        header = parts[0]
        _, _, rounds_str = header.split(":")
        return int(rounds_str) < PBKDF2_ROUNDS
    except Exception:
        return True


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed RFC 7519 HS256 JWT access token.
    """
    secret_key = get_jwt_secret_key()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    })

    header = {"alg": "HS256", "typ": "JWT"}
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    header_b64 = _base64url_encode(header_bytes)
    payload_b64 = _base64url_encode(payload_bytes)

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode, cryptographically verify, and validate an RFC 7519 HS256 JWT token.
    Strictly validates:
    - Exactly 3 dot-separated segments
    - Valid base64url encoding
    - Valid JSON in header and payload
    - Algorithm MUST be 'HS256' (blocks algorithm confusion and 'none' attacks)
    - Type MUST be 'JWT' (if specified)
    - HMAC-SHA256 signature match via constant-time comparison
    - Required non-empty 'sub' claim
    - Valid, unexpired 'exp' timestamp
    Raises ValueError on any failure.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Token must be a non-empty string.")

    segments = token.split(".")
    if len(segments) != 3:
        raise ValueError("Invalid JWT token structure: must contain exactly 3 segments.")

    header_b64, payload_b64, signature_b64 = segments

    # 1. Decode and strictly validate header
    try:
        header_bytes = _base64url_decode(header_b64)
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Malformed JWT header: {exc}")

    if not isinstance(header, dict):
        raise ValueError("JWT header must be a JSON object.")

    if header.get("alg") != "HS256":
        raise ValueError(f"Unsupported algorithm '{header.get('alg')}'. Only 'HS256' is permitted.")

    if header.get("typ") and header.get("typ").upper() != "JWT":
        raise ValueError(f"Unsupported token type '{header.get('typ')}'. Expected 'JWT'.")

    # 2. Cryptographic signature verification
    secret_key = get_jwt_secret_key()
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()
    expected_sig_b64 = _base64url_encode(expected_signature)

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        raise ValueError("Invalid token signature.")

    # 3. Decode and validate payload
    try:
        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Malformed JWT payload: {exc}")

    if not isinstance(payload, dict):
        raise ValueError("JWT payload must be a JSON object.")

    # 4. Validate required subject claim
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str) or not sub.strip():
        raise ValueError("Token payload missing required non-empty 'sub' claim.")

    # 5. Validate expiration claim
    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Token payload missing required 'exp' claim.")
    if not isinstance(exp, (int, float)):
        raise ValueError("Token 'exp' claim must be an integer timestamp.")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > exp:
        raise ValueError("Token has expired.")

    return payload
