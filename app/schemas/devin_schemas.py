"""
Pydantic models for Devin API structured outputs.
These schemas define the JSON structure Devin will populate.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from datetime import datetime


class PlanStep(BaseModel):
    """A single step in the implementation plan."""
    step: str = Field(..., description="Description of the step")
    rationale: str = Field(..., description="Why this step is necessary")


class RiskAssessment(BaseModel):
    """Risk assessment for implementing the issue."""
    level: Literal["low", "medium", "high"] = Field(..., description="Risk level")
    reasons: List[str] = Field(default_factory=list, description="List of risk factors")


class ScopingOutput(BaseModel):
    """
    Simplified structured output schema for scoping sessions.
    This is what Devin will populate during the scoping phase.
    """
    summary: str = Field(..., description="Brief summary of what needs to be done")
    plan: List[str] = Field(
        default_factory=list,
        description="List of implementation steps (3-7 steps recommended)"
    )
    risk_level: str = Field(..., description="Risk level: low, medium, or high")
    est_effort_hours: float = Field(
        ...,
        description="Estimated effort in hours",
        ge=0.0
    )
    confidence: float = Field(
        ...,
        description="Confidence score for successful implementation (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    
    @field_validator("plan")
    @classmethod
    def validate_plan_length(cls, v: List[str]) -> List[str]:
        """Ensure plan has reasonable number of steps."""
        if len(v) > 20:
            raise ValueError("Plan should have at most 20 steps for maintainability")
        return v
    
    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        """Ensure risk level is valid."""
        if v.lower() not in ["low", "medium", "high"]:
            raise ValueError("Risk level must be 'low', 'medium', or 'high'")
        return v.lower()


class CommitInfo(BaseModel):
    """Information about a commit made during execution."""
    sha: str = Field(..., description="Commit SHA")
    message: str = Field(..., description="Commit message")


class TestResults(BaseModel):
    """Test execution results."""
    passed: int = Field(default=0, description="Number of tests passed", ge=0)
    failed: int = Field(default=0, description="Number of tests failed", ge=0)
    skipped: int = Field(default=0, description="Number of tests skipped", ge=0)


class PRInfo(BaseModel):
    """Information about the pull request."""
    url: str = Field(..., description="PR URL")
    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    number: Optional[int] = Field(None, description="PR number")


class ExecutionOutput(BaseModel):
    """
    Simplified structured output schema for execution sessions.
    Devin updates this as it makes progress implementing the issue.
    """
    status: Literal[
        "planning",
        "coding",
        "testing",
        "done"
    ] = Field(default="planning", description="Current execution status")
    branch: Optional[str] = Field(None, description="Feature branch name")
    pr_url: Optional[str] = Field(None, description="Pull request URL")
    tests_passed: int = Field(default=0, description="Number of tests passed", ge=0)
    tests_failed: int = Field(default=0, description="Number of tests failed", ge=0)
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete."""
        return self.status == "done" and self.pr_url is not None


class DevinSession(BaseModel):
    """
    Response model for Devin session creation/status.
    Matches the Devin API response structure from Cognition's qa-devin example.
    """
    session_id: str = Field(..., description="Unique session identifier")
    status: Optional[str] = Field(None, description="Human-readable session status")
    status_enum: Optional[Literal[
        "working",
        "blocked", 
        "finished",
        "suspend_requested",
        "resume_requested",
        "resumed",
        "stopped"
    ]] = Field(None, description="Machine-readable status enum")
    title: Optional[str] = Field(None, description="Session title")
    created_at: Optional[datetime] = Field(None, description="Session creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    snapshot_id: Optional[str] = Field(None, description="Snapshot ID if available")
    playbook_id: Optional[str] = Field(None, description="Playbook ID if used")
    structured_output: Optional[dict] = Field(None, description="Structured output JSON")
    url: Optional[str] = Field(None, description="Session URL (returned on creation)")
    is_new_session: Optional[bool] = Field(None, description="Whether this is a new session")
    messages: Optional[List[dict]] = Field(None, description="List of session messages")
    
    
class DevinSessionCreate(BaseModel):
    """Request model for creating a Devin session."""
    prompt: str = Field(..., description="The task prompt for Devin")
    playbook_id: Optional[str] = Field(None, description="Playbook to use")
    structured_output_schema: Optional[dict] = Field(
        None,
        description="JSON schema for structured output"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for the session")
    idempotent: bool = Field(
        default=True,
        description="Whether to reuse existing session with same prompt"
    )
    attachments: List[str] = Field(
        default_factory=list,
        description="List of attachment URLs"
    )


class DevinMessage(BaseModel):
    """Request model for sending a message to a Devin session."""
    message: str = Field(..., description="Message to send to Devin")
