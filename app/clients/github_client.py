"""
GitHub API client for interacting with issues, comments, and labels.
Handles authentication, rate limiting, retries, and error handling.
"""

import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
from functools import wraps
import time

from app.config import get_settings
from app.schemas.github_schemas import (
    GitHubIssue,
    GitHubComment,
    GitHubLabel,
    GitHubPullRequest,
    GitHubRepository,
)

logger = logging.getLogger(__name__)


class GitHubRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class GitHubAPIError(Exception):
    """General GitHub API error."""
    pass


def retry_on_rate_limit(max_retries: int = 3, backoff_factor: float = 2.0):
    """
    Decorator to retry API calls on rate limit errors with exponential backoff.
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except GitHubRateLimitError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Rate limit hit, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Max retries reached for rate limit")
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except GitHubRateLimitError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Rate limit hit, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Max retries reached for rate limit")
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class GitHubClient:
    """
    Client for interacting with the GitHub REST API.
    Handles authentication, pagination, rate limiting, and error handling.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub client.
        
        Args:
            token: GitHub Personal Access Token. If None, loads from settings.
        """
        settings = get_settings()
        self.token = token or settings.github_token
        self.base_url = "https://api.github.com"
        self.rate_limit_buffer = settings.github_rate_limit_buffer
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        # Rate limit tracking
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[datetime] = None
        
        logger.info("GitHub client initialized")
    
    def _check_rate_limit(self, response: httpx.Response) -> None:
        """
        Check and update rate limit information from response headers.
        
        Args:
            response: HTTP response from GitHub API
            
        Raises:
            GitHubRateLimitError: If rate limit is exceeded
        """
        if "X-RateLimit-Remaining" in response.headers:
            self._rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
        
        if "X-RateLimit-Reset" in response.headers:
            reset_timestamp = int(response.headers["X-RateLimit-Reset"])
            self._rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
        
        # Log warning if getting close to rate limit
        if self._rate_limit_remaining is not None:
            if self._rate_limit_remaining < self.rate_limit_buffer:
                logger.warning(
                    f"GitHub API rate limit low: {self._rate_limit_remaining} remaining"
                )
            
            if self._rate_limit_remaining == 0:
                wait_seconds = (
                    (self._rate_limit_reset - datetime.now()).total_seconds()
                    if self._rate_limit_reset
                    else 3600
                )
                raise GitHubRateLimitError(
                    f"GitHub API rate limit exceeded. "
                    f"Resets in {wait_seconds:.0f} seconds."
                )
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle API response and check for errors.
        
        Args:
            response: HTTP response from GitHub API
            
        Returns:
            Parsed JSON response
            
        Raises:
            GitHubRateLimitError: If rate limit exceeded
            GitHubAPIError: For other API errors
        """
        self._check_rate_limit(response)
        
        if response.status_code == 403 and "rate limit" in response.text.lower():
            raise GitHubRateLimitError("Rate limit exceeded")
        
        if response.status_code == 404:
            raise GitHubAPIError(f"Resource not found: {response.url}")
        
        if response.status_code >= 400:
            error_msg = f"GitHub API error {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise GitHubAPIError(error_msg)
        
        return response.json()
    
    @retry_on_rate_limit(max_retries=3)
    def list_issues(
        self,
        owner: str,
        repo: str,
        label: Optional[str] = None,
        state: str = "open",
        assignee: Optional[str] = None,
        since: Optional[datetime] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> List[GitHubIssue]:
        """
        List issues from a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            label: Filter by label name
            state: Filter by state (open/closed/all)
            assignee: Filter by assignee username
            since: Filter by updated since datetime
            per_page: Results per page (max 100)
            page: Page number
            
        Returns:
            List of GitHubIssue objects
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        
        params: Dict[str, Any] = {
            "state": state,
            "per_page": min(per_page, 100),
            "page": page,
        }
        
        if label:
            params["labels"] = label
        if assignee:
            params["assignee"] = assignee
        if since:
            params["since"] = since.isoformat()
        
        logger.info(f"Listing issues for {owner}/{repo} with params: {params}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers, params=params)
            data = self._handle_response(response)
        
        # Filter out pull requests (GitHub issues API includes PRs)
        issues = [
            GitHubIssue(**item)
            for item in data
            if "pull_request" not in item
        ]
        
        logger.info(f"Retrieved {len(issues)} issues from {owner}/{repo}")
        return issues
    
    @retry_on_rate_limit(max_retries=3)
    def get_issue(
        self,
        owner: str,
        repo: str,
        number: int,
    ) -> GitHubIssue:
        """
        Get a specific issue by number.
        
        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number
            
        Returns:
            GitHubIssue object
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{number}"
        
        logger.info(f"Getting issue {owner}/{repo}#{number}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers)
            data = self._handle_response(response)
        
        return GitHubIssue(**data)
    
    @retry_on_rate_limit(max_retries=3)
    def get_issue_comments(
        self,
        owner: str,
        repo: str,
        number: int,
        per_page: int = 100,
    ) -> List[GitHubComment]:
        """
        Get comments for a specific issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number
            per_page: Results per page (max 100)
            
        Returns:
            List of GitHubComment objects
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/comments"
        
        params = {"per_page": min(per_page, 100)}
        
        logger.info(f"Getting comments for issue {owner}/{repo}#{number}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers, params=params)
            data = self._handle_response(response)
        
        comments = [GitHubComment(**item) for item in data]
        logger.info(f"Retrieved {len(comments)} comments")
        return comments
    
    @retry_on_rate_limit(max_retries=3)
    def create_comment(
        self,
        owner: str,
        repo: str,
        number: int,
        body: str,
    ) -> GitHubComment:
        """
        Create a comment on an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number
            body: Comment text (supports markdown)
            
        Returns:
            Created GitHubComment object
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/comments"
        
        payload = {"body": body}
        
        logger.info(f"Creating comment on issue {owner}/{repo}#{number}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=self.headers, json=payload)
            data = self._handle_response(response)
        
        logger.info(f"Comment created: {data.get('id')}")
        return GitHubComment(**data)
    
    @retry_on_rate_limit(max_retries=3)
    def add_labels(
        self,
        owner: str,
        repo: str,
        number: int,
        labels: List[str],
    ) -> List[GitHubLabel]:
        """
        Add labels to an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number
            labels: List of label names to add
            
        Returns:
            Updated list of all labels on the issue
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/labels"
        
        payload = {"labels": labels}
        
        logger.info(f"Adding labels {labels} to issue {owner}/{repo}#{number}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=self.headers, json=payload)
            data = self._handle_response(response)
        
        return [GitHubLabel(**item) for item in data]
    
    @retry_on_rate_limit(max_retries=3)
    def set_labels(
        self,
        owner: str,
        repo: str,
        number: int,
        labels: List[str],
    ) -> List[GitHubLabel]:
        """
        Set (replace) labels on an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number
            labels: List of label names to set (replaces existing)
            
        Returns:
            Updated list of labels on the issue
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/labels"
        
        payload = {"labels": labels}
        
        logger.info(f"Setting labels {labels} on issue {owner}/{repo}#{number}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.put(url, headers=self.headers, json=payload)
            data = self._handle_response(response)
        
        return [GitHubLabel(**item) for item in data]
    
    @retry_on_rate_limit(max_retries=3)
    def remove_label(
        self,
        owner: str,
        repo: str,
        number: int,
        label: str,
    ) -> None:
        """
        Remove a specific label from an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            number: Issue number
            label: Label name to remove
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{number}/labels/{label}"
        
        logger.info(f"Removing label '{label}' from issue {owner}/{repo}#{number}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(url, headers=self.headers)
            
            if response.status_code == 404:
                logger.warning(f"Label '{label}' not found on issue")
                return
            
            self._check_rate_limit(response)
            
            if response.status_code >= 400:
                raise GitHubAPIError(f"Failed to remove label: {response.text}")
    
    @retry_on_rate_limit(max_retries=3)
    def create_label(
        self,
        owner: str,
        repo: str,
        name: str,
        color: str,
        description: Optional[str] = None,
    ) -> GitHubLabel:
        """
        Create a new label in the repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            name: Label name
            color: Label color (6-character hex code without #)
            description: Optional label description
            
        Returns:
            Created GitHubLabel object
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/labels"
        
        payload = {
            "name": name,
            "color": color.lstrip("#"),
        }
        if description:
            payload["description"] = description
        
        logger.info(f"Creating label '{name}' in {owner}/{repo}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=self.headers, json=payload)
            data = self._handle_response(response)
        
        return GitHubLabel(**data)
    
    @retry_on_rate_limit(max_retries=3)
    def get_repository(
        self,
        owner: str,
        repo: str,
    ) -> GitHubRepository:
        """
        Get repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            GitHubRepository object
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        logger.info(f"Getting repository info for {owner}/{repo}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers)
            data = self._handle_response(response)
        
        return GitHubRepository(**data)
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        return {
            "remaining": self._rate_limit_remaining,
            "reset_at": self._rate_limit_reset.isoformat() if self._rate_limit_reset else None,
        }
