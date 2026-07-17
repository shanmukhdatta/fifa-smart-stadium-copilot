"""Request/response models for the copilot chat endpoint."""

from typing import Literal

from pydantic import BaseModel, Field

SUPPORTED_LANGUAGES = {"en", "es", "fr", "ar", "pt", "hi"}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    language: str = Field(default="en")
    location: str | None = Field(
        default=None, max_length=200, description="Free-text location, e.g. 'Gate 4'"
    )
    accessibility_needs: list[str] = Field(default_factory=list)

    def normalized_language(self) -> str:
        return self.language if self.language in SUPPORTED_LANGUAGES else "en"


class AgentResult(BaseModel):
    agent: str
    summary: str
    confidence: float
    details: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response_text: str
    language: str
    agents_used: list[str]
    agent_results: list[AgentResult]
    voice_ready_text: str
    confidence: float
    request_id: str


class ErrorResponse(BaseModel):
    error: str
    request_id: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str
    role: Literal["fan", "volunteer", "staff", "organizer"] = "fan"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
