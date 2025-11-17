"""
API routes for the orchestrator.
Endpoints: /scope, /execute, /sessions, /issues
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.database import get_db_session
from app.models import Issue, Session as DBSession, Event, SessionPhase, SessionStatus
from app.clients import GitHubClient, DevinClient
from app.schemas.devin_schemas import ScopingOutput, ExecutionOutput
from app.schemas.github_schemas import GitHubIssue, IssueListParams
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class ScopeIssueRequest(BaseModel):
    """Request to scope an issue."""
    repo: str = Field(..., description="Repository (owner/name)")
    issue_number: int = Field(..., description="Issue number")


class ExecuteIssueRequest(BaseModel):
    """Request to execute an issue."""
    repo: str = Field(..., description="Repository (owner/name)")
    issue_number: int = Field(..., description="Issue number")
    session_id: Optional[str] = Field(None, description="Optional session ID to resume")


class SessionResponse(BaseModel):
    """Response containing session information."""
    session_id: str
    repo: str
    issue_number: int
    phase: str
    status: str
    message: str
    session_url: Optional[str] = None


class ScopeResponse(SessionResponse):
    """Response from scoping operation."""
    scoping_output: Optional[dict] = None


class ExecuteResponse(SessionResponse):
    """Response from execution operation."""
    execution_output: Optional[dict] = None


# Helper Functions
def log_event(db: Session, session_id: str, kind: str, payload: dict):
    """Log an event to the database."""
    event = Event(
        session_id=session_id,
        kind=kind,
        payload=payload,
    )
    db.add(event)
    db.commit()


def update_issue_in_db(
    db: Session,
    repo: str,
    issue_number: int,
    github_issue: GitHubIssue,
    confidence_score: Optional[float] = None,
):
    """Update or create issue in database."""
    issue = db.query(Issue).filter_by(repo=repo, number=issue_number).first()
    
    if not issue:
        issue = Issue(repo=repo, number=issue_number)
        db.add(issue)
    
    issue.title = github_issue.title
    issue.state = github_issue.state
    issue.labels = [label.name for label in github_issue.labels]
    issue.assignee = github_issue.assignee.login if github_issue.assignee else None
    issue.author = github_issue.user.login
    issue.url = github_issue.html_url
    issue.updated_at = github_issue.updated_at
    
    if confidence_score is not None:
        issue.confidence_score = confidence_score
    
    db.commit()
    return issue


# Routes
@router.get("/issues")
async def list_issues(
    repo: str,
    label: Optional[str] = None,
    state: str = "open",
    assignee: Optional[str] = None,
    page: int = 1,
    per_page: int = 30,
    db: Session = Depends(get_db_session),
):
    """
    List GitHub issues with filters.
    
    This endpoint fetches issues from GitHub and returns them with any
    tracked metadata (like confidence scores) from our database.
    """
    try:
        # Parse repo
        if "/" not in repo:
            raise HTTPException(status_code=400, detail="Repo must be in format 'owner/name'")
        
        owner, repo_name = repo.split("/", 1)
        
        # Fetch from GitHub
        github_client = GitHubClient()
        issues = github_client.list_issues(
            owner=owner,
            repo=repo_name,
            label=label,
            state=state,
            assignee=assignee,
            per_page=per_page,
            page=page,
        )
        
        # Enrich with database info
        result = []
        for issue in issues:
            db_issue = db.query(Issue).filter_by(
                repo=repo,
                number=issue.number
            ).first()
            
            issue_dict = issue.dict()
            if db_issue:
                issue_dict["confidence_score"] = db_issue.confidence_score
                issue_dict["last_scoped_at"] = db_issue.last_scoped_at
                issue_dict["last_executed_at"] = db_issue.last_executed_at
            else:
                issue_dict["confidence_score"] = None
                issue_dict["last_scoped_at"] = None
                issue_dict["last_executed_at"] = None
            
            result.append(issue_dict)
        
        return {
            "repo": repo,
            "issues": result,
            "page": page,
            "per_page": per_page,
            "count": len(result),
        }
    
    except Exception as e:
        logger.error(f"Error listing issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scope", response_model=ScopeResponse)
async def scope_issue(
    request: ScopeIssueRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    Trigger a Devin scoping session for an issue.
    
    This creates a Devin session that analyzes the issue and returns:
    - Implementation plan
    - Confidence score
    - Risk assessment
    - Effort estimate
    """
    try:
        # Parse repo
        if "/" not in request.repo:
            raise HTTPException(status_code=400, detail="Repo must be in format 'owner/name'")
        
        owner, repo_name = request.repo.split("/", 1)
        
        # Fetch issue from GitHub
        github_client = GitHubClient()
        github_issue = github_client.get_issue(owner, repo_name, request.issue_number)
        
        # Get comments
        comments = github_client.get_issue_comments(owner, repo_name, request.issue_number)
        comment_texts = [c.body for c in comments]
        
        # Update issue in DB
        update_issue_in_db(db, request.repo, request.issue_number, github_issue)
        
        # Create Devin scoping session
        devin_client = DevinClient()
        session = devin_client.create_scoping_session(
            issue_number=request.issue_number,
            repo=request.repo,
            issue_title=github_issue.title,
            issue_body=github_issue.body or "",
            comments=comment_texts,
        )
        
        # Store session in database (check if already exists due to idempotency)
        db_session = db.query(DBSession).filter_by(session_id=session.session_id).first()
        if not db_session:
            # Create new session
            db_session = DBSession(
                session_id=session.session_id,
                phase=SessionPhase.SCOPE,
                repo=request.repo,
                issue_number=request.issue_number,
                status=SessionStatus.CREATED,
                title=session.title,
                tags=session.session_id,
                prompt="",
            )
            db.add(db_session)
        else:
            # Update existing session
            db_session.status = SessionStatus.CREATED
            db_session.updated_at = datetime.now()
            logger.info(f"Reusing existing scoping session: {session.session_id}")
        
        db.commit()
        
        # Log event
        log_event(db, session.session_id, "session_created", {
            "phase": "scope",
            "repo": request.repo,
            "issue_number": request.issue_number,
        })
        
        # Post comment to GitHub
        comment_body = f"""🤖 **Devin Scoping Session Started**

I'm analyzing this issue to create an implementation plan.

- **Session ID**: `{session.session_id}`
- **Session URL**: {session.url or 'N/A'}
- **Status**: Working...

I'll update this comment when the scoping is complete with:
- Implementation plan
- Confidence score
- Risk assessment
- Estimated effort

---
*Powered by [Devin AI](https://devin.ai)*
"""
        github_client.create_comment(owner, repo_name, request.issue_number, comment_body)
        
        return ScopeResponse(
            session_id=session.session_id,
            repo=request.repo,
            issue_number=request.issue_number,
            phase="scope",
            status=session.status or session.status_enum or "working",
            message="Scoping session created successfully",
            session_url=session.url,
        )
    
    except Exception as e:
        logger.error(f"Error scoping issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteResponse)
async def execute_issue(
    request: ExecuteIssueRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    Trigger a Devin execution session for an issue.
    
    This creates a Devin session that implements the issue by:
    - Creating a feature branch
    - Implementing changes
    - Running tests
    - Opening a PR
    """
    try:
        # Parse repo
        if "/" not in request.repo:
            raise HTTPException(status_code=400, detail="Repo must be in format 'owner/name'")
        
        owner, repo_name = request.repo.split("/", 1)
        
        # Fetch issue from GitHub
        github_client = GitHubClient()
        github_issue = github_client.get_issue(owner, repo_name, request.issue_number)
        
        # Get scoping session if available
        scoping_session = db.query(DBSession).filter_by(
            repo=request.repo,
            issue_number=request.issue_number,
            phase=SessionPhase.SCOPE,
        ).order_by(DBSession.created_at.desc()).first()
        
        scoping_plan = {}
        if scoping_session and scoping_session.last_structured_output:
            # Handle if stored as JSON string or already parsed dict
            if isinstance(scoping_session.last_structured_output, str):
                import json
                try:
                    scoping_plan = json.loads(scoping_session.last_structured_output)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse scoping_plan as JSON: {scoping_session.last_structured_output}")
                    scoping_plan = {}
            else:
                scoping_plan = scoping_session.last_structured_output
        
        # Create Devin execution session
        devin_client = DevinClient()
        session = devin_client.create_execution_session(
            issue_number=request.issue_number,
            repo=request.repo,
            issue_title=github_issue.title,
            scoping_plan=scoping_plan,
        )
        
        # Store session in database (check if already exists due to idempotency)
        db_session = db.query(DBSession).filter_by(session_id=session.session_id).first()
        if not db_session:
            # Create new session
            db_session = DBSession(
                session_id=session.session_id,
                phase=SessionPhase.EXEC,
                repo=request.repo,
                issue_number=request.issue_number,
                status=SessionStatus.CREATED,
                title=session.title,
                tags=session.session_id,
                prompt="",
            )
            db.add(db_session)
        else:
            # Update existing session
            db_session.status = SessionStatus.CREATED
            db_session.updated_at = datetime.now()
            logger.info(f"Reusing existing execution session: {session.session_id}")
        
        db.commit()
        
        # Update issue timestamp
        db_issue = db.query(Issue).filter_by(
            repo=request.repo,
            number=request.issue_number
        ).first()
        if db_issue:
            db_issue.last_executed_at = datetime.now()
            db.commit()
        
        # Log event
        log_event(db, session.session_id, "session_created", {
            "phase": "exec",
            "repo": request.repo,
            "issue_number": request.issue_number,
        })
        
        # Post comment to GitHub
        comment_body = f"""🚀 **Devin Execution Session Started**

I'm implementing this issue now!

- **Session ID**: `{session.session_id}`
- **Session URL**: {session.url or 'N/A'}
- **Status**: Working...

I'll:
1. Create a feature branch
2. Implement the changes
3. Run tests and linting
4. Open a Pull Request

Stay tuned for updates!

---
*Powered by [Devin AI](https://devin.ai)*
"""
        github_client.create_comment(owner, repo_name, request.issue_number, comment_body)
        
        return ExecuteResponse(
            session_id=session.session_id,
            repo=request.repo,
            issue_number=request.issue_number,
            phase="exec",
            status=session.status or session.status_enum or "working",
            message="Execution session created successfully",
            session_url=session.url,
        )
    
    except Exception as e:
        logger.error(f"Error executing issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session_status(
    session_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get the status of a Devin session.
    
    Returns the current status, structured output, and metadata.
    If structured_output is null, attempts to parse it from messages.
    """
    try:
        # Get from Devin
        devin_client = DevinClient()
        session = devin_client.get_session(session_id)
        
        # Fallback: If structured_output is null, try parsing from messages
        structured_output = session.structured_output
        if not structured_output:
            from app.clients.message_parser import parse_scoping_from_messages, parse_execution_from_messages
            
            # Try to extract from messages
            db_session = db.query(DBSession).filter_by(session_id=session_id).first()
            if db_session:
                if db_session.phase == SessionPhase.SCOPE:
                    structured_output = parse_scoping_from_messages(getattr(session, 'messages', []))
                elif db_session.phase == SessionPhase.EXEC:
                    structured_output = parse_execution_from_messages(getattr(session, 'messages', []))
                
                if structured_output:
                    logger.info(f"Extracted structured output from messages for session {session_id}")
        
        # Update database
        db_session = db.query(DBSession).filter_by(session_id=session_id).first()
        if db_session:
            db_session.status = SessionStatus.RUNNING if session.status_enum == "working" else SessionStatus.BLOCKED
            db_session.last_structured_output = structured_output
            db_session.updated_at = datetime.now()
            
            # Update issue confidence if scoping session
            if db_session.phase == SessionPhase.SCOPE and structured_output:
                confidence = structured_output.get("confidence")
                if confidence is not None:
                    db_issue = db.query(Issue).filter_by(
                        repo=db_session.repo,
                        number=db_session.issue_number
                    ).first()
                    if db_issue:
                        db_issue.confidence_score = confidence
                        db_issue.last_scoped_at = datetime.now()
            
            db.commit()
        
        return {
            "session_id": session.session_id,
            "status": session.status,
            "status_enum": session.status_enum,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "structured_output": structured_output,  # Use the parsed output if original was null
            "url": session.url,
        }
    
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/poll")
async def poll_session(
    session_id: str,
    timeout: int = 1800,
    db: Session = Depends(get_db_session),
):
    """
    Poll a session until it reaches a terminal state.
    
    This is a long-running endpoint that will wait until the session
    completes, blocks, or times out.
    """
    try:
        devin_client = DevinClient()
        
        def update_callback(session):
            """Update database on each poll."""
            db_session = db.query(DBSession).filter_by(session_id=session_id).first()
            if db_session:
                db_session.last_structured_output = session.structured_output
                db_session.updated_at = datetime.now()
                db.commit()
        
        # Poll until complete
        final_session = devin_client.poll_session(
            session_id=session_id,
            timeout=timeout,
            callback=update_callback,
        )
        
        # Update final status
        db_session = db.query(DBSession).filter_by(session_id=session_id).first()
        if db_session:
            if final_session.status_enum == "finished":
                db_session.status = SessionStatus.FINISHED
                db_session.finished_at = datetime.now()
            elif final_session.status_enum == "blocked":
                db_session.status = SessionStatus.BLOCKED
            
            db.commit()
        
        return {
            "session_id": final_session.session_id,
            "status": final_session.status,
            "status_enum": final_session.status_enum,
            "structured_output": final_session.structured_output,
            "message": f"Session reached terminal state: {final_session.status_enum}",
        }
    
    except Exception as e:
        logger.error(f"Error polling session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
