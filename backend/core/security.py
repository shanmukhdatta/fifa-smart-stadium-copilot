"""
Security primitives used across the app.

Scope is deliberately kept to what an MVP can actually deliver and prove
in a live demo:
  - JWT issuing / verification (no OAuth provider wiring -- out of scope)
  - A single role claim used for coarse RBAC (fan / volunteer / staff)
  - A lightweight prompt-injection heuristic guard
  - PII redaction helper for safe logging
  - Password hashing (for the demo login endpoint)

None of this claims to be a full OWASP-compliant auth system. It is real,
working code for the pieces that are actually exercised by the app.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.core.config import settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

VALID_ROLES = {"fan", "volunteer", "staff", "organizer"}


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------

def create_access_token(subject: str, role: str) -> str:
    if role not in VALID_ROLES:
        raise ValueError(f"Unknown role: {role}")
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        # Never leak internal error detail to the client.
        logger.warning("JWT decode failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return {"user_id": user_id, "role": role}


def require_role(*allowed_roles: str):
    """RBAC dependency factory: Depends(require_role('staff', 'organizer'))."""

    async def _check(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return user

    return _check


# --------------------------------------------------------------------------
# Prompt injection guard
# --------------------------------------------------------------------------

# Pattern-based heuristic -- not a silver bullet, but catches the common,
# unsophisticated jailbreak/override attempts an MVP is realistically
# tested against. Runs BEFORE the message reaches the planner.
_INJECTION_PATTERNS = [
    r"ignore (all|any|previous|prior) instructions",
    r"disregard (all|any|previous|prior) (instructions|rules)",
    r"you are now",
    r"system prompt",
    r"reveal (your|the) (system )?prompt",
    r"act as (?!a translator|an accessibility)",
    r"jailbreak",
    r"override (safety|security|guardrails)",
    r"pretend (you|to) (have no|bypass)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


class PromptInjectionError(ValueError):
    pass


def log_security_event(event_type: str, details: str, severity: str = "INFO") -> None:
    """
    Structured security event and audit logging.
    """
    log_msg = f"[SECURITY EVENT] type={event_type} severity={severity} details={details}"
    if severity == "WARNING":
        logger.warning(log_msg)
    elif severity == "ERROR":
        logger.error(log_msg)
    else:
        logger.info(log_msg)


def validate_output(text: str) -> str:
    """
    Output Validation & Hallucination Guardrails:
    1. Prevents system prompt/instruction leakage.
    2. Flags/blocks hallucinated gate names (e.g. Gate 5, Gate 6, etc.).
    """
    # 1. Leakage checks
    leakage_patterns = [
        r"system prompt", r"ignore previous instructions", r"you are a helpful stadium assistant"
    ]
    for pattern in leakage_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            log_security_event(
                "OUTPUT_VALIDATION_FAILURE",
                "System prompt/instruction leakage pattern matched in output",
                severity="WARNING"
            )
            return "I'm sorry, I cannot output this message as it violates security policies."

    # 2. Gate hallucination check (matches gates other than Gate 1, Gate 2, Gate 3, Gate 4)
    match = re.search(r"\bGate\s+([5-9]|\d{2,})\b", text, re.IGNORECASE)
    if match:
        hallucinated_gate = match.group(0)
        log_security_event(
            "OUTPUT_VALIDATION_FAILURE",
            f"Hallucinated gate detected in output: {hallucinated_gate}",
            severity="WARNING"
        )
        return "I'm sorry, the response generated contained incorrect stadium layout details. Please re-query."

    return text


def check_prompt_injection(text: str) -> None:
    if _INJECTION_RE.search(text):
        log_security_event(
            "PROMPT_INJECTION_DETECTED",
            "Inbound message matched prompt injection pattern",
            severity="WARNING"
        )
        raise PromptInjectionError(
            "Your message could not be processed. Please rephrase your request."
        )


# --------------------------------------------------------------------------
# PII redaction (for logging only -- not for user-facing responses)
# --------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\b\d{10}\b|\+\d{1,3}[\s-]?\d{9,10}\b")


def redact(text: str) -> str:
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text
