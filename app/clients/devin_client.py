"""
Devin API client for creating and managing sessions.
Handles session creation, polling, structured output, and messaging.
"""

import httpx
import logging
import asyncio
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from functools import wraps

from app.config import get_settings
from app.schemas.devin_schemas import (
    DevinSession,
    DevinSessionCreate,
    DevinMessage,
)

logger = logging.getLogger(__name__)


class DevinAPIError(Exception):
    """General Devin API error."""
    pass


class DevinSessionError(Exception):
    """Error related to Devin session operations."""
    pass


class DevinTimeoutError(Exception):
    """Raised when polling times out."""
    pass


def retry_on_server_error(max_retries: int = 3, backoff_factor: float = 2.0):
    """
    Decorator to retry API calls on 5xx server errors with exponential backoff.
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except DevinAPIError as e:
                    # Only retry on 5xx errors
                    if "5" in str(e) and attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Server error, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        last_exception = e
                    else:
                        raise
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except DevinAPIError as e:
                    # Only retry on 5xx errors
                    if "5" in str(e) and attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Server error, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        last_exception = e
                    else:
                        raise
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class DevinClient:
    """
    Client for interacting with the Devin API.
    Handles session management, polling, and structured output.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize the Devin client.
        
        Args:
            api_key: Devin API key. If None, loads from settings.
            api_url: Devin API base URL. If None, loads from settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.devin_api_key
        self.base_url = (api_url or settings.devin_api_url).rstrip("/")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Polling configuration
        self.default_poll_interval = settings.devin_poll_interval
        self.default_poll_timeout = settings.devin_poll_timeout
        self.max_poll_interval = settings.devin_poll_max_interval
        
        logger.info(f"Devin client initialized with base URL: {self.base_url}")
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle API response and check for errors.
        
        Args:
            response: HTTP response from Devin API
            
        Returns:
            Parsed JSON response
            
        Raises:
            DevinAPIError: For API errors
        """
        if response.status_code == 400:
            error_msg = f"Bad request: {response.text}"
            logger.error(error_msg)
            raise DevinAPIError(error_msg)
        
        if response.status_code == 401:
            error_msg = "Unauthorized: Invalid API key"
            logger.error(error_msg)
            raise DevinAPIError(error_msg)
        
        if response.status_code == 404:
            error_msg = f"Resource not found: {response.url}"
            logger.error(error_msg)
            raise DevinAPIError(error_msg)
        
        if response.status_code >= 500:
            error_msg = f"Server error {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise DevinAPIError(error_msg)
        
        if response.status_code >= 400:
            error_msg = f"API error {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise DevinAPIError(error_msg)
        
        try:
            return response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise DevinAPIError(f"Invalid JSON response: {e}")
    
    @retry_on_server_error(max_retries=3)
    def create_session(
        self,
        prompt: str,
        playbook_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        idempotent: bool = True,
        attachments: Optional[List[str]] = None,
    ) -> DevinSession:
        """
        Create a new Devin session.
        
        Args:
            prompt: The task prompt for Devin (include structured output schema here)
            playbook_id: Optional playbook ID to use
            tags: List of tags for the session
            title: Session title
            idempotent: Whether to reuse existing session with same prompt
            attachments: List of attachment URLs
            
        Returns:
            DevinSession object with session details
        """
        url = f"{self.base_url}/sessions"
        
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "idempotent": idempotent,
        }
        
        if playbook_id:
            payload["playbook_id"] = playbook_id
        
        if tags:
            payload["tags"] = tags
        
        if title:
            payload["title"] = title
        
        if attachments:
            payload["attachments"] = attachments
        
        logger.info(f"Creating Devin session with title: {title or 'Untitled'}")
        logger.debug(f"Session payload: {payload}")
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=self.headers, json=payload)
            data = self._handle_response(response)
        
        session = DevinSession(**data)
        logger.info(f"Session created: {session.session_id}")
        return session
    
    @retry_on_server_error(max_retries=3)
    def get_session(self, session_id: str) -> DevinSession:
        """
        Get session details and status.
        
        Args:
            session_id: Devin session ID
            
        Returns:
            DevinSession object with current status and output
        """
        # Use plural /sessions/ endpoint as per API documentation
        url = f"{self.base_url}/sessions/{session_id}"
        
        logger.debug(f"Getting session: {session_id}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers)
            data = self._handle_response(response)
        
        return DevinSession(**data)
    
    def poll_session(
        self,
        session_id: str,
        interval: Optional[int] = None,
        timeout: Optional[int] = None,
        callback: Optional[Callable[[DevinSession], None]] = None,
    ) -> DevinSession:
        """
        Poll a session until it reaches a terminal state.
        
        Terminal states: 'finished', 'blocked', 'stopped'
        Based on Cognition team's qa-devin example implementation.
        
        Args:
            session_id: Devin session ID
            interval: Initial polling interval in seconds (uses default if None)
            timeout: Maximum time to poll in seconds (uses default if None)
            callback: Optional callback function called on each poll with session data
            
        Returns:
            Final DevinSession object
            
        Raises:
            DevinTimeoutError: If polling times out
        """
        interval = interval or self.default_poll_interval
        timeout = timeout or self.default_poll_timeout
        
        start_time = time.time()
        current_interval = interval
        # Terminal states based on Cognition's qa-devin example
        terminal_states = {'finished', 'blocked', 'stopped'}
        
        logger.info(
            f"Starting to poll session {session_id} "
            f"(interval: {interval}s, timeout: {timeout}s)"
        )
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                raise DevinTimeoutError(
                    f"Polling timed out after {timeout}s for session {session_id}"
                )
            
            session = self.get_session(session_id)
            
            # Prefer status_enum (machine-readable) over status (human-readable)
            if session.status_enum:
                status_str = session.status_enum.lower()
            elif session.status:
                status_str = session.status.lower()
            else:
                status_str = "unknown"
            
            logger.debug(f"Session {session_id} status_enum: {status_str}")
            
            # Call callback if provided
            if callback:
                try:
                    callback(session)
                except Exception as e:
                    logger.warning(f"Callback error: {e}")
            
            # Check if terminal state reached using status_enum
            if status_str in terminal_states:
                logger.info(
                    f"Session {session_id} reached terminal state: {status_str}"
                )
                return session
            
            # Wait before next poll with exponential backoff
            logger.debug(f"Waiting {current_interval}s before next poll")
            time.sleep(current_interval)
            
            # Increase interval with exponential backoff, up to max
            current_interval = min(current_interval * 1.5, self.max_poll_interval)
    
    @retry_on_server_error(max_retries=3)
    def send_message(
        self,
        session_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Send a message to a Devin session (nudge/resume).
        
        Args:
            session_id: Devin session ID
            message: Message to send to Devin
            
        Returns:
            Response data
        """
        url = f"{self.base_url}/sessions/{session_id}/message"
        
        payload = {"message": message}
        
        logger.info(f"Sending message to session {session_id}")
        logger.debug(f"Message: {message[:100]}...")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=self.headers, json=payload)
            data = self._handle_response(response)
        
        logger.info(f"Message sent to session {session_id}")
        return data
    
    @retry_on_server_error(max_retries=3)
    def update_tags(
        self,
        session_id: str,
        tags: List[str],
    ) -> Dict[str, Any]:
        """
        Update tags for a session.
        
        Args:
            session_id: Devin session ID
            tags: List of tags to set
            
        Returns:
            Response data
        """
        url = f"{self.base_url}/sessions/{session_id}/tags"
        
        payload = {"tags": tags}
        
        logger.info(f"Updating tags for session {session_id}: {tags}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.put(url, headers=self.headers, json=payload)
            data = self._handle_response(response)
        
        return data
    
    @retry_on_server_error(max_retries=3)
    def get_session_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a session.
        
        Args:
            session_id: Devin session ID
            limit: Optional limit on number of messages
            
        Returns:
            List of message objects
        """
        url = f"{self.base_url}/sessions/{session_id}/messages"
        
        params = {}
        if limit:
            params["limit"] = limit
        
        logger.info(f"Getting messages for session {session_id}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers, params=params)
            data = self._handle_response(response)
        
        messages = data if isinstance(data, list) else data.get("messages", [])
        logger.info(f"Retrieved {len(messages)} messages")
        return messages
    
    @retry_on_server_error(max_retries=3)
    def create_attachment(
        self,
        content: bytes,
        filename: str,
        content_type: str = "text/plain",
    ) -> str:
        """
        Upload an attachment to Devin.
        
        Args:
            content: File content as bytes
            filename: File name
            content_type: MIME type of the content
            
        Returns:
            Attachment URL to reference in prompts
        """
        url = f"{self.base_url}/attachments"
        
        files = {
            "file": (filename, content, content_type)
        }
        
        # Note: For file upload, we use multipart/form-data instead of JSON
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        logger.info(f"Uploading attachment: {filename}")
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, files=files)
            data = self._handle_response(response)
        
        attachment_url = data.get("url", "")
        logger.info(f"Attachment uploaded: {attachment_url}")
        return attachment_url
    
    def create_scoping_session(
        self,
        issue_number: int,
        repo: str,
        issue_title: str,
        issue_body: str,
        comments: List[str],
        knowledge_refs: Optional[List[str]] = None,
    ) -> DevinSession:
        """
        Helper method to create a scoping session with standard parameters.
        
        Args:
            issue_number: GitHub issue number
            repo: Repository (owner/name)
            issue_title: Issue title
            issue_body: Issue description
            comments: List of comment texts
            knowledge_refs: Optional knowledge note references
            
        Returns:
            DevinSession object
        """
        prompt = self._build_scoping_prompt(
            issue_number=issue_number,
            repo=repo,
            issue_title=issue_title,
            issue_body=issue_body,
            comments=comments,
        )
        
        tags = [
            f"issue-{issue_number}",
            f"repo:{repo}",
            "phase:scope",
        ]
        
        title = f"Scope Issue #{issue_number}: {issue_title[:50]}"
        
        return self.create_session(
            prompt=prompt,
            tags=tags,
            title=title,
            idempotent=True,
        )
    
    def create_execution_session(
        self,
        issue_number: int,
        repo: str,
        issue_title: str,
        scoping_plan: Dict[str, Any],
    ) -> DevinSession:
        """
        Helper method to create an execution session with standard parameters.
        
        Args:
            issue_number: GitHub issue number
            repo: Repository (owner/name)
            issue_title: Issue title
            scoping_plan: The plan from scoping phase
            
        Returns:
            DevinSession object
        """
        prompt = self._build_execution_prompt(
            issue_number=issue_number,
            repo=repo,
            issue_title=issue_title,
            scoping_plan=scoping_plan,
        )
        
        tags = [
            f"issue-{issue_number}",
            f"repo:{repo}",
            "phase:exec",
        ]
        
        title = f"Execute Issue #{issue_number}: {issue_title[:50]}"
        
        return self.create_session(
            prompt=prompt,
            tags=tags,
            title=title,
            idempotent=True,
        )
    
    def _build_scoping_prompt(
        self,
        issue_number: int,
        repo: str,
        issue_title: str,
        issue_body: str,
        comments: List[str],
    ) -> str:
        """Build the scoping prompt from issue data."""
        comments_text = "\n\n".join(
            f"Comment {i+1}:\n{comment}"
            for i, comment in enumerate(comments[:20])
        ) if comments else "No comments yet."
        
        import json
        
        schema = {
            "summary": "Brief summary of what needs to be done",
            "plan": ["Step 1", "Step 2", "Step 3"],
            "risk_level": "medium",
            "est_effort_hours": 8.0,
            "confidence": 0.75
        }
        
        return f"""You are triaging GitHub issue #{issue_number} in {repo}.

**IMPORTANT**: This is ANALYSIS ONLY. Do NOT write any code, do NOT create branches, do NOT open PRs. Just analyze and plan.

**Issue Details**:
- **Title**: {issue_title}
- **Number**: #{issue_number}
- **Repository**: {repo}

**Description**:
{issue_body or "No description provided."}

**Comments**:
{comments_text}

**Your Task - ANALYSIS ONLY**:
Analyze this issue and provide your assessment in this format. Please update the structured output immediately when you complete your analysis:
{json.dumps(schema)}

Provide:
1. A brief summary of what needs to be done
2. A 3-7 step plan describing how to implement it (but DO NOT implement it yourself)
3. Risk level assessment (low/medium/high)
4. Estimated effort in hours
5. Confidence score (0.0 to 1.0) for successful implementation

This is SCOPING only - do not write code or make changes. Just analyze and plan."""
    
    def _build_execution_prompt(
        self,
        issue_number: int,
        repo: str,
        issue_title: str,
        scoping_plan: Dict[str, Any],
    ) -> str:
        """Build the execution prompt from scoping data."""
        plan_text = "\n".join(
            f"{i+1}. {step.get('step', 'N/A')}: {step.get('rationale', 'N/A')}"
            for i, step in enumerate(scoping_plan.get("plan", []))
        ) if scoping_plan.get("plan") else "No plan available."
        
        dod_text = "\n".join(
            f"- {item}"
            for item in scoping_plan.get("definition_of_done", [])
        ) if scoping_plan.get("definition_of_done") else "- Complete implementation\n- Tests pass"
        
        import json
        
        schema = {
            "status": "planning",
            "branch": "feature-branch-name",
            "pr_url": None,
            "tests_passed": 0,
            "tests_failed": 0
        }
        
        return f"""Implement GitHub issue #{issue_number} in {repo}.

**Issue**: {issue_title}

**Implementation Plan**:
{plan_text}

**Definition of Done**:
{dod_text}

**Your Task**:
Implement the changes and provide updates in this format. Please update the structured output immediately when you create the branch, run tests, or open a PR:
{json.dumps(schema)}

Create a feature branch, implement the changes, write/update tests, and open a PR. Update status as you progress: planning → coding → testing → done"""
