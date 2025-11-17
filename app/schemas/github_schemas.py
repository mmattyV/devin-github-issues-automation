"""
Pydantic models for GitHub API responses.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime


class GitHubUser(BaseModel):
    """GitHub user/account information."""
    login: str = Field(..., description="Username")
    id: int = Field(..., description="User ID")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    url: Optional[str] = Field(None, description="API URL")
    html_url: Optional[str] = Field(None, description="Profile URL")


class GitHubLabel(BaseModel):
    """GitHub issue label."""
    id: Optional[int] = Field(None, description="Label ID")
    name: str = Field(..., description="Label name")
    color: Optional[str] = Field(None, description="Label color (hex)")
    description: Optional[str] = Field(None, description="Label description")


class GitHubComment(BaseModel):
    """GitHub issue comment."""
    id: int = Field(..., description="Comment ID")
    body: str = Field(..., description="Comment text")
    user: GitHubUser = Field(..., description="Comment author")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    html_url: Optional[str] = Field(None, description="Comment URL")


class GitHubIssue(BaseModel):
    """GitHub issue representation."""
    number: int = Field(..., description="Issue number")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(None, description="Issue description")
    state: str = Field(..., description="Issue state (open/closed)")
    user: GitHubUser = Field(..., description="Issue author")
    labels: List[GitHubLabel] = Field(default_factory=list, description="Issue labels")
    assignee: Optional[GitHubUser] = Field(None, description="Assigned user")
    assignees: List[GitHubUser] = Field(default_factory=list, description="All assignees")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    closed_at: Optional[datetime] = Field(None, description="Closed timestamp")
    html_url: str = Field(..., description="Issue URL")
    comments: int = Field(default=0, description="Number of comments")
    
    @property
    def repo_from_url(self) -> Optional[str]:
        """Extract owner/repo from the issue URL."""
        try:
            # URL format: https://github.com/owner/repo/issues/123
            parts = self.html_url.split("/")
            if len(parts) >= 5 and "github.com" in parts[2]:
                return f"{parts[3]}/{parts[4]}"
        except:
            pass
        return None


class GitHubPullRequest(BaseModel):
    """GitHub pull request representation."""
    number: int = Field(..., description="PR number")
    title: str = Field(..., description="PR title")
    body: Optional[str] = Field(None, description="PR description")
    state: str = Field(..., description="PR state (open/closed)")
    user: GitHubUser = Field(..., description="PR author")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    merged_at: Optional[datetime] = Field(None, description="Merge timestamp")
    html_url: str = Field(..., description="PR URL")
    head: dict = Field(..., description="Head branch info")
    base: dict = Field(..., description="Base branch info")
    draft: bool = Field(default=False, description="Is draft PR")


class GitHubCommitStatus(BaseModel):
    """GitHub commit status."""
    state: str = Field(..., description="Status state (pending/success/error/failure)")
    target_url: Optional[str] = Field(None, description="Link to details")
    description: Optional[str] = Field(None, description="Status description")
    context: str = Field(..., description="Status context/identifier")


class GitHubRepository(BaseModel):
    """GitHub repository information."""
    id: int = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full name (owner/repo)")
    owner: GitHubUser = Field(..., description="Repository owner")
    html_url: str = Field(..., description="Repository URL")
    description: Optional[str] = Field(None, description="Repository description")
    private: bool = Field(..., description="Is private repository")
    default_branch: str = Field(default="main", description="Default branch name")


class IssueListParams(BaseModel):
    """Parameters for listing issues."""
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    label: Optional[str] = Field(None, description="Filter by label")
    state: str = Field(default="open", description="Filter by state (open/closed/all)")
    assignee: Optional[str] = Field(None, description="Filter by assignee")
    since: Optional[datetime] = Field(None, description="Filter by updated since")
    per_page: int = Field(default=30, description="Results per page", ge=1, le=100)
    page: int = Field(default=1, description="Page number", ge=1)


class CommentCreateRequest(BaseModel):
    """Request to create a comment."""
    body: str = Field(..., description="Comment text", min_length=1)


class LabelUpdateRequest(BaseModel):
    """Request to update issue labels."""
    labels: List[str] = Field(..., description="List of label names to set")
