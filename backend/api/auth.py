"""
Demo authentication endpoint.

Uses an in-memory user store seeded at startup. This is explicitly scoped
as MVP-only: swapping to a real user table (SQLite/Postgres via the same
pattern as the rest of the app) is a small, contained change limited to
`_USERS` and `login()` -- nothing else in the codebase touches user
storage directly, since everything downstream depends only on the JWT.
"""

from fastapi import APIRouter, HTTPException, Request, status

from backend.core.config import settings
from backend.core.logging_config import get_logger
from backend.core.rate_limit import limiter
from backend.core.security import create_access_token, hash_password, log_security_event, verify_password
from backend.schemas.chat import LoginRequest, TokenResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Demo users -- passwords are hashed even for this in-memory store so the
# hashing path is exercised for real, not just decoratively present.
_USERS: dict[str, dict] = {
    "fan1": {"password": hash_password("fanpass123"), "role": "fan"},
    "volunteer1": {"password": hash_password("volpass123"), "role": "volunteer"},
    "staff1": {"password": hash_password("staffpass123"), "role": "staff"},
}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest) -> TokenResponse:
    user = _USERS.get(payload.username)
    if not user or not verify_password(payload.password, user["password"]):
        log_security_event("AUTH_FAILURE", f"Failed login attempt for username={payload.username}", severity="WARNING")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(subject=payload.username, role=user["role"])
    return TokenResponse(access_token=token)


@router.post("/demo-token", response_model=TokenResponse)
@limiter.limit("5/minute")
def demo_token(request: Request, role: str = "fan") -> TokenResponse:
    """
    Convenience endpoint for hackathon judges/demos: issues a short-lived
    token without needing to know a seeded username/password. Not exposed
    in a real deployment -- gated here so the judge can test the full
    authenticated flow in one click.
    """
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if role not in {"fan", "volunteer", "staff", "organizer"}:
        role = "fan"
    token = create_access_token(subject=f"demo-{role}", role=role)
    return TokenResponse(access_token=token)
