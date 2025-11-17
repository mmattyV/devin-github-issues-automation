"""
SQLAlchemy ORM models for database tables.
Tables: issues, sessions, events, settings
"""

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Float, 
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum


Base = declarative_base()


class SessionPhase(str, enum.Enum):
    """Enum for session phases."""
    SCOPE = "scope"
    EXEC = "exec"


class SessionStatus(str, enum.Enum):
    """Enum for session statuses."""
    CREATED = "created"
    RUNNING = "running"
    BLOCKED = "blocked"
    FINISHED = "finished"
    EXPIRED = "expired"
    FAILED = "failed"


class Issue(Base):
    """
    GitHub issues that have been tracked by the system.
    Primary key is (repo, number) composite.
    """
    __tablename__ = "issues"
    
    repo = Column(String(255), primary_key=True, nullable=False, index=True)
    number = Column(Integer, primary_key=True, nullable=False)
    title = Column(String(512), nullable=True)
    state = Column(String(50), nullable=True)  # open, closed
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    labels = Column(JSON, nullable=True, default=[])  # List of label names
    assignee = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    url = Column(String(512), nullable=True)
    confidence_score = Column(Float, nullable=True)  # Last known confidence score
    last_scoped_at = Column(DateTime, nullable=True)
    last_executed_at = Column(DateTime, nullable=True)
    tracked_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("idx_repo_state", "repo", "state"),
        Index("idx_repo_updated", "repo", "updated_at"),
    )


class Session(Base):
    """
    Devin sessions (both scoping and execution).
    Tracks the lifecycle and outputs of Devin API sessions.
    """
    __tablename__ = "sessions"
    
    session_id = Column(String(255), primary_key=True, nullable=False)
    phase = Column(SQLEnum(SessionPhase), nullable=False, index=True)
    repo = Column(String(255), nullable=False, index=True)
    issue_number = Column(Integer, nullable=False, index=True)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.CREATED)
    
    # Devin session details
    title = Column(String(512), nullable=True)
    tags = Column(JSON, nullable=True, default=[])  # List of tags
    
    # Structured output from Devin
    last_structured_output = Column(JSON, nullable=True)
    
    # Metadata
    prompt = Column(Text, nullable=True)  # Initial prompt sent to Devin
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    
    # GitHub integration
    github_comment_id = Column(Integer, nullable=True)  # ID of comment posted to issue
    github_pr_number = Column(Integer, nullable=True)  # PR number if created
    
    __table_args__ = (
        Index("idx_repo_issue", "repo", "issue_number"),
        Index("idx_phase_status", "phase", "status"),
    )


class Event(Base):
    """
    Event log for auditing and debugging.
    Tracks all significant events in the system.
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    kind = Column(String(100), nullable=False, index=True)  # e.g., "session_created", "status_changed"
    payload = Column(JSON, nullable=True)  # Flexible JSON storage for event data
    
    __table_args__ = (
        Index("idx_kind_timestamp", "kind", "timestamp"),
    )


class RepoSettings(Base):
    """
    Per-repository configuration settings.
    Stores repository-specific preferences and defaults.
    """
    __tablename__ = "settings"
    
    repo = Column(String(255), primary_key=True, nullable=False)
    
    # Label management
    labels_to_manage = Column(JSON, nullable=True, default=[])  # Labels to auto-create/manage
    
    # Playbook preferences
    default_scope_playbook = Column(String(255), nullable=True)
    default_exec_playbook = Column(String(255), nullable=True)
    
    # PR template hints
    pr_template_hint = Column(Text, nullable=True)
    
    # Knowledge references
    knowledge_refs = Column(JSON, nullable=True, default=[])  # List of knowledge note IDs
    
    # Automation settings
    auto_scope_on_label = Column(String(100), nullable=True)  # Auto-scope if this label added
    auto_execute_threshold = Column(Float, nullable=True)  # Auto-execute if confidence > threshold
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
