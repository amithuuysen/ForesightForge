from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ClaimStatus = Literal["proposed", "supported", "contested", "rejected", "verified"]


class ResearchRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=240)
    question: str = Field(min_length=8, max_length=1200)
    model_provider: str | None = Field(default=None, max_length=64)
    model_name: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, max_length=400)
    # FR-IN-1: "problem" or "topic". Omit to let the intake classifier decide.
    mode: Literal["problem", "topic", "auto"] = Field(default="auto")
    # FR-IN-3: run limits.
    depth: Literal["quick", "standard", "deep"] = Field(default="standard")
    max_usd: float = Field(default=5.0, gt=0, le=50)
    max_rounds: int = Field(default=2, ge=1, le=8)
    max_queries: int = Field(default=3, ge=1, le=8)
    max_sources: int = Field(default=6, ge=1, le=20)


class CheckpointDecision(BaseModel):
    """A human decision on a pending checkpoint (FR-UX-2)."""

    run_id: str
    checkpoint_id: str = ""
    action: Literal["approve", "edit", "reject", "redirect", "select", "auto_select"] = "approve"
    selected_ids: list[str] = Field(default_factory=list)
    edits: dict[str, str] = Field(default_factory=dict)
    note: str = Field(default="", max_length=2000)
    redirect: str = Field(default="", max_length=2000)


class RunControlRequest(BaseModel):
    """Pause, resume or cancel a run (FR-UX-3)."""

    run_id: str
    action: Literal["pause", "resume", "cancel"]


class SourceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str
    title: str
    excerpt: str = ""
    content: str = ""
    search_snippet: str = ""
    published_at: str | None = None
    publisher: str = ""
    query: str = ""
    provider: str = ""
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClaimRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    status: ClaimStatus = "proposed"
    confidence: float = Field(ge=0, le=1)
    author: str
    source_ids: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)


class RunRecord(BaseModel):
    id: str
    domain: str
    question: str
    status: Literal["running", "completed", "needs_evidence", "failed"]
    round: int = 1
    current_stage: str = "gather"
    created_at: datetime
    updated_at: datetime
    claims: list[ClaimRecord] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    audit: list[dict[str, str]] = Field(default_factory=list)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)