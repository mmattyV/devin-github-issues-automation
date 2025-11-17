#!/usr/bin/env python3
"""
Example usage script demonstrating the Devin GitHub Issues Automation system.

This shows how to use the system programmatically (not via CLI).
"""

import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.clients import GitHubClient, DevinClient
from app.database import get_db, init_db
from app.models import Issue, Session, SessionPhase, SessionStatus
from rich.console import Console
from rich.table import Table

console = Console()


def example_1_list_issues():
    """Example 1: List issues from a repository."""
    console.print("\n[bold cyan]Example 1: List Issues[/bold cyan]\n")
    
    github = GitHubClient()
    
    # List open bugs from python/cpython
    issues = github.list_issues(
        owner="python",
        repo="cpython",
        label="type-bug",
        state="open",
        per_page=5
    )
    
    # Display in a table
    table = Table(title="Open Bugs in python/cpython")
    table.add_column("#", style="cyan")
    table.add_column("Title")
    table.add_column("Author", style="green")
    
    for issue in issues:
        table.add_row(
            f"#{issue.number}",
            issue.title[:60] + "..." if len(issue.title) > 60 else issue.title,
            issue.user.login
        )
    
    console.print(table)
    console.print(f"\n✓ Found {len(issues)} issues\n")


def example_2_scope_issue():
    """Example 2: Scope an issue (without waiting for result)."""
    console.print("\n[bold cyan]Example 2: Scope an Issue[/bold cyan]\n")
    
    github = GitHubClient()
    devin = DevinClient()
    
    # Get an issue
    issue = github.get_issue("python", "cpython", 100000)
    
    console.print(f"Issue: [bold]#{issue.number}[/bold] - {issue.title}")
    console.print(f"State: {issue.state}\n")
    
    # Get comments
    comments = github.get_issue_comments("python", "cpython", 100000)
    comment_texts = [c.body for c in comments]
    
    # Create scoping session
    console.print("Creating Devin scoping session...")
    session = devin.create_scoping_session(
        issue_number=issue.number,
        repo="python/cpython",
        issue_title=issue.title,
        issue_body=issue.body or "",
        comments=comment_texts
    )
    
    console.print(f"✓ Session created: [cyan]{session.session_id}[/cyan]")
    if session.url:
        console.print(f"View at: {session.url}")
    
    console.print("\n[dim]Note: Session is running in background. ")
    console.print("Use devin.get_session(session_id) to check status.[/dim]\n")


def example_3_check_session_status():
    """Example 3: Check status of a Devin session."""
    console.print("\n[bold cyan]Example 3: Check Session Status[/bold cyan]\n")
    
    # This is a demo - replace with a real session ID
    session_id = "demo-session-id"
    
    console.print(f"To check a session's status:\n")
    console.print(f"[dim]from app.clients import DevinClient")
    console.print(f"devin = DevinClient()")
    console.print(f"session = devin.get_session('{session_id}')")
    console.print(f"print(session.status)")
    console.print(f"print(session.structured_output)[/dim]\n")


def example_4_query_database():
    """Example 4: Query the database for tracked sessions."""
    console.print("\n[bold cyan]Example 4: Query Database[/bold cyan]\n")
    
    # Initialize database
    init_db()
    
    with get_db() as db:
        # Count sessions by phase
        scope_count = db.query(Session).filter_by(phase=SessionPhase.SCOPE).count()
        exec_count = db.query(Session).filter_by(phase=SessionPhase.EXEC).count()
        
        console.print(f"Sessions in database:")
        console.print(f"  - Scoping sessions: {scope_count}")
        console.print(f"  - Execution sessions: {exec_count}")
        
        # Get high-confidence issues
        high_conf_issues = db.query(Issue).filter(
            Issue.confidence_score >= 0.8
        ).all()
        
        console.print(f"\nHigh-confidence issues (≥80%): {len(high_conf_issues)}")
        
        for issue in high_conf_issues[:5]:
            console.print(f"  - {issue.repo}#{issue.number}: {issue.confidence_score:.0%}")
    
    console.print()


def example_5_create_github_comment():
    """Example 5: Post a comment to a GitHub issue."""
    console.print("\n[bold cyan]Example 5: Create GitHub Comment[/bold cyan]\n")
    
    console.print("To post a comment:\n")
    console.print("[dim]github = GitHubClient()")
    console.print('comment = github.create_comment(')
    console.print('    owner="myorg",')
    console.print('    repo="myrepo",')
    console.print('    number=123,')
    console.print('    body="🤖 Devin is working on this issue!"')
    console.print(')')
    console.print('print(f"Comment posted: {comment.html_url}")[/dim]\n')


def example_6_poll_session():
    """Example 6: Poll a session until complete."""
    console.print("\n[bold cyan]Example 6: Poll Until Complete[/bold cyan]\n")
    
    console.print("To wait for a session to complete:\n")
    console.print("[dim]devin = DevinClient()")
    console.print()
    console.print("def progress_callback(session):")
    console.print('    print(f"Status: {session.status}")')
    console.print()
    console.print('final_session = devin.poll_session(')
    console.print('    session_id="abc123",')
    console.print('    timeout=1800,  # 30 minutes')
    console.print('    callback=progress_callback')
    console.print(')')
    console.print()
    console.print('print("Completed!")')
    console.print('print(final_session.structured_output)[/dim]\n')


def example_7_batch_scope():
    """Example 7: Scope multiple issues in batch."""
    console.print("\n[bold cyan]Example 7: Batch Scope Issues[/bold cyan]\n")
    
    console.print("To scope multiple issues:\n")
    console.print("[dim]github = GitHubClient()")
    console.print("devin = DevinClient()")
    console.print()
    console.print('# Get all open bugs')
    console.print('issues = github.list_issues("myorg", "myrepo", label="bug")')
    console.print()
    console.print('sessions = []')
    console.print('for issue in issues:')
    console.print('    session = devin.create_scoping_session(')
    console.print('        issue_number=issue.number,')
    console.print('        repo="myorg/myrepo",')
    console.print('        issue_title=issue.title,')
    console.print('        issue_body=issue.body or "",')
    console.print('        comments=[]')
    console.print('    )')
    console.print('    sessions.append(session)')
    console.print('    print(f"Scoping #{issue.number}")')
    console.print()
    console.print('print(f"Created {len(sessions)} scoping sessions!")[/dim]\n')


def main():
    """Run all examples."""
    console.print("\n[bold green]Devin GitHub Issues Automation - Example Usage[/bold green]")
    console.print("[dim]This demonstrates how to use the system programmatically[/dim]\n")
    
    try:
        example_1_list_issues()
        example_2_scope_issue()
        example_3_check_session_status()
        example_4_query_database()
        example_5_create_github_comment()
        example_6_poll_session()
        example_7_batch_scope()
        
        console.print("[bold green]✓ All examples completed![/bold green]\n")
        console.print("💡 Tips:")
        console.print("  - Use the CLI for interactive workflows")
        console.print("  - Use the Python API for automation scripts")
        console.print("  - Check the orchestrator API docs at http://localhost:8000/docs")
        console.print()
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("\n[yellow]Make sure:")
        console.print("  1. .env is configured with API keys")
        console.print("  2. Orchestrator is running (uvicorn app.api.main:app)")
        console.print("  3. Database is initialized[/yellow]\n")


if __name__ == "__main__":
    main()

