"""
CLI application using Typer.
Commands: list, scope, execute
"""

import typer
import httpx
import time
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint
from datetime import datetime

app = typer.Typer(
    name="devin-issues",
    help="🤖 Automate GitHub issue triaging and execution with Devin AI",
    add_completion=False,
)

console = Console()

# Default orchestrator URL
DEFAULT_ORCHESTRATOR_URL = "http://localhost:8000"


def get_orchestrator_url(url: Optional[str] = None) -> str:
    """Get the orchestrator URL from argument or environment."""
    import os
    return url or os.getenv("ORCHESTRATOR_URL", DEFAULT_ORCHESTRATOR_URL)


def format_datetime(dt_str: Optional[str]) -> str:
    """Format datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_str


def format_confidence(score: Optional[float]) -> str:
    """Format confidence score with color."""
    if score is None:
        return "[dim]N/A[/dim]"
    
    color = "red" if score < 0.5 else "yellow" if score < 0.8 else "green"
    percentage = f"{score * 100:.0f}%"
    return f"[{color}]{percentage}[/{color}]"


@app.command()
def list(
    repo: str = typer.Argument(..., help="Repository in format 'owner/name'"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by label"),
    state: str = typer.Option("open", "--state", "-s", help="Filter by state (open/closed/all)"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="Filter by assignee"),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    per_page: int = typer.Option(30, "--per-page", help="Results per page"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Orchestrator URL"),
):
    """
    📋 List GitHub issues with filters.
    
    Examples:
        devin-issues list owner/repo
        devin-issues list owner/repo --label bug --state open
        devin-issues list owner/repo --assignee username
    """
    orchestrator_url = get_orchestrator_url(url)
    
    console.print(f"\n[bold cyan]📋 Listing issues for {repo}[/bold cyan]\n")
    
    try:
        # Make API request
        with console.status("[bold green]Fetching issues from GitHub..."):
            response = httpx.get(
                f"{orchestrator_url}/api/v1/issues",
                params={
                    "repo": repo,
                    "label": label,
                    "state": state,
                    "assignee": assignee,
                    "page": page,
                    "per_page": per_page,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        
        issues = data.get("issues", [])
        
        if not issues:
            console.print("[yellow]No issues found matching the criteria.[/yellow]")
            return
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("#", style="cyan", width=6)
        table.add_column("Title", style="white", overflow="fold")
        table.add_column("Labels", style="blue", width=20)
        table.add_column("Confidence", justify="center", width=12)
        table.add_column("Updated", style="dim", width=16)
        
        for issue in issues:
            # Format labels
            labels_data = issue.get("labels", [])
            if labels_data:
                # Labels come as list of dicts with 'name' field from the API
                if isinstance(labels_data[0], dict):
                    label_names = [label.get("name", label) for label in labels_data[:3]]
                else:
                    label_names = labels_data[:3]
                labels = ", ".join(label_names)
                if len(labels_data) > 3:
                    labels += "..."
            else:
                labels = ""
            
            # Format title (truncate if too long)
            title = issue.get("title", "")
            if len(title) > 60:
                title = title[:57] + "..."
            
            table.add_row(
                f"#{issue.get('number')}",
                title,
                labels or "[dim]none[/dim]",
                format_confidence(issue.get("confidence_score")),
                format_datetime(issue.get("updated_at")),
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(issues)} issues (page {page})[/dim]")
        console.print(f"[dim]Use --page {page + 1} to see more[/dim]\n")
        
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]❌ HTTP Error {e.response.status_code}:[/bold red] {e.response.text}")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[bold red]❌ Connection Error:[/bold red] {str(e)}")
        console.print(f"[yellow]Make sure the orchestrator is running at {orchestrator_url}[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def scope(
    repo: str = typer.Argument(..., help="Repository in format 'owner/name'"),
    issue: int = typer.Argument(..., help="Issue number"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for scoping to complete"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Orchestrator URL"),
):
    """
    🔍 Scope an issue with Devin AI.
    
    This triggers Devin to analyze the issue and return:
    - Implementation plan with steps
    - Confidence score (0-100%)
    - Risk assessment
    - Effort estimate
    - Dependencies and blockers
    
    Examples:
        devin-issues scope owner/repo 123
        devin-issues scope owner/repo 456 --no-wait
    """
    orchestrator_url = get_orchestrator_url(url)
    
    console.print(f"\n[bold cyan]🔍 Scoping issue {repo}#{issue}[/bold cyan]\n")
    
    try:
        # Create scoping session
        with console.status("[bold green]Creating Devin scoping session..."):
            response = httpx.post(
                f"{orchestrator_url}/api/v1/scope",
                json={"repo": repo, "issue_number": issue},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        
        session_id = data.get("session_id")
        session_url = data.get("session_url")
        
        console.print(f"[green]✓[/green] Session created: [cyan]{session_id}[/cyan]")
        if session_url:
            console.print(f"[dim]View session:[/dim] {session_url}\n")
        
        if not wait:
            console.print("[yellow]Session started in background. Check status later with:[/yellow]")
            console.print(f"[dim]  curl {orchestrator_url}/api/v1/sessions/{session_id}[/dim]\n")
            return
        
        # Poll for completion
        console.print("[bold]Waiting for Devin to complete scoping...[/bold]")
        console.print("[dim](This may take 2-5 minutes)[/dim]\n")
        
        start_time = time.time()
        poll_count = 0
        timed_out = False
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Analyzing issue...", total=None)
            
            while True:
                time.sleep(10)  # Poll every 10 seconds
                poll_count += 1
                elapsed = int(time.time() - start_time)
                
                progress.update(task, description=f"[cyan]Analyzing issue... ({elapsed}s, poll #{poll_count})")
                
                try:
                    # Get status (increased timeout for slow responses)
                    with httpx.Client(timeout=90.0) as client:
                        status_response = client.get(
                            f"{orchestrator_url}/api/v1/sessions/{session_id}"
                        )
                        status_response.raise_for_status()
                        status_data = status_response.json()
                    
                    status_enum = status_data.get("status_enum", "").lower()
                    
                    if status_enum in ["finished", "blocked", "stopped"]:
                        break
                    
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    # Network issue - log and continue polling
                    progress.update(task, description=f"[yellow]Connection issue, retrying... ({elapsed}s, poll #{poll_count})[/yellow]")
                    continue
                except httpx.HTTPStatusError as e:
                    console.print(f"[red]✗[/red] HTTP Error {e.response.status_code}: {e.response.text}")
                    raise typer.Exit(1)
                
                if elapsed > 600:  # 10 minutes timeout
                    timed_out = True
                    break
        
        elapsed = int(time.time() - start_time)
        
        # Handle timeout gracefully
        if timed_out:
            console.print(f"\n[yellow]⏱️  Polling timeout after {elapsed // 60} minutes.[/yellow]")
            console.print(f"[dim]Devin is still analyzing this issue in the background.[/dim]\n")
            console.print(f"[bold cyan]Check progress at:[/bold cyan]")
            console.print(f"  [dim]•[/dim] Session: {session_url or session_id}")
            console.print(f"  [dim]•[/dim] GitHub issue comments will be updated automatically")
            console.print(f"  [dim]•[/dim] Re-run this command later to check status\n")
            return
        
        # Get final results (increased timeout)
        try:
            with httpx.Client(timeout=90.0) as client:
                final_response = client.get(
                    f"{orchestrator_url}/api/v1/sessions/{session_id}"
                )
                final_response.raise_for_status()
                final_data = final_response.json()
        except Exception as e:
            console.print(f"\n[yellow]⚠️  Could not fetch final results: {str(e)}[/yellow]")
            console.print(f"[dim]Check session at: {session_url or session_id}[/dim]\n")
            return
        
        structured_output = final_data.get("structured_output") or {}
        status_enum = final_data.get("status_enum", "").lower()
        
        # Determine completion message
        if status_enum == "finished":
            console.print(f"\n[bold green]✓ Scoping complete![/bold green] (took {elapsed}s)\n")
        elif status_enum == "blocked":
            console.print(f"\n[bold yellow]⚠️  Devin is blocked[/bold yellow] (after {elapsed}s)\n")
            console.print("[dim]Devin may need input or encountered an issue. Check the session.[/dim]\n")
        else:
            console.print(f"\n[bold cyan]Session Status: {status_enum}[/bold cyan] (after {elapsed}s)\n")
        
        # Display results
        if structured_output:
            # Summary
            summary = structured_output.get("summary", "N/A")
            console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="blue"))
            
            # Confidence and effort
            confidence = structured_output.get("confidence", 0)
            effort = structured_output.get("est_effort_hours", 0)
            
            console.print(f"\n[bold]Confidence Score:[/bold] {format_confidence(confidence)}")
            console.print(f"[bold]Estimated Effort:[/bold] {effort} hours")
            
            # Risk (simplified - now just a string)
            risk_level = structured_output.get("risk_level", "unknown").upper()
            risk_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}.get(risk_level, "white")
            console.print(f"[bold]Risk Level:[/bold] [{risk_color}]{risk_level}[/{risk_color}]")
            
            # Plan (simplified - now just a list of strings)
            plan = structured_output.get("plan", [])
            if plan:
                console.print("\n[bold cyan]📋 Implementation Plan:[/bold cyan]")
                for i, step in enumerate(plan, 1):
                    # Plan is now a simple list of strings
                    console.print(f"  [cyan]{i}.[/cyan] {step}")
            
            console.print()
        else:
            console.print("[yellow]No structured output available yet.[/yellow]")
        
        console.print(f"[dim]Full details: {session_url or 'See orchestrator logs'}[/dim]\n")
        
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]❌ HTTP Error {e.response.status_code}:[/bold red] {e.response.text}")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[bold red]❌ Connection Error:[/bold red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def execute(
    repo: str = typer.Argument(..., help="Repository in format 'owner/name'"),
    issue: int = typer.Argument(..., help="Issue number"),
    wait: bool = typer.Option(False, "--wait/--no-wait", help="Wait for execution to complete"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Orchestrator URL"),
):
    """
    🚀 Execute an issue with Devin AI.
    
    This triggers Devin to implement the issue by:
    - Creating a feature branch
    - Making code changes
    - Running tests
    - Opening a Pull Request
    
    Examples:
        devin-issues execute owner/repo 123
        devin-issues execute owner/repo 456 --wait
    """
    orchestrator_url = get_orchestrator_url(url)
    
    console.print(f"\n[bold cyan]🚀 Executing issue {repo}#{issue}[/bold cyan]\n")
    
    try:
        # Create execution session
        with console.status("[bold green]Creating Devin execution session..."):
            response = httpx.post(
                f"{orchestrator_url}/api/v1/execute",
                json={"repo": repo, "issue_number": issue},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        
        session_id = data.get("session_id")
        session_url = data.get("session_url")
        
        console.print(f"[green]✓[/green] Execution session created: [cyan]{session_id}[/cyan]")
        if session_url:
            console.print(f"[dim]View session:[/dim] {session_url}\n")
        
        console.print("[bold green]🎉 Devin is now working on this issue![/bold green]")
        console.print("\n[yellow]This will take 10-30 minutes. Devin will:[/yellow]")
        console.print("  1. Create a feature branch")
        console.print("  2. Implement the changes")
        console.print("  3. Run tests and linting")
        console.print("  4. Open a Pull Request")
        console.print("  5. Post updates to the GitHub issue\n")
        
        if not wait:
            console.print("[dim]Check progress at:[/dim] " + (session_url or f"{orchestrator_url}/api/v1/sessions/{session_id}"))
            console.print()
            return
        
        # Poll for completion (long-running)
        console.print("[bold]Waiting for Devin to complete execution...[/bold]")
        console.print("[dim](This may take 10-30 minutes)[/dim]\n")
        
        start_time = time.time()
        poll_count = 0
        last_status = None
        timed_out = False
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Implementing issue...", total=None)
            
            while True:
                time.sleep(15)  # Poll every 15 seconds
                poll_count += 1
                elapsed = int(time.time() - start_time)
                
                try:
                    # Get status (increased timeout for slow responses)
                    with httpx.Client(timeout=90.0) as client:
                        status_response = client.get(
                            f"{orchestrator_url}/api/v1/sessions/{session_id}"
                        )
                        status_response.raise_for_status()
                        status_data = status_response.json()
                    
                    status_enum = status_data.get("status_enum", "").lower()
                    structured_output = status_data.get("structured_output", {})
                    current_status = structured_output.get("status", "working") if structured_output else "working"
                    
                    # Update progress message
                    if current_status != last_status:
                        progress.update(task, description=f"[cyan]{current_status.replace('_', ' ').title()}... ({elapsed}s)")
                        last_status = current_status
                    else:
                        progress.update(task, description=f"[cyan]{current_status.replace('_', ' ').title()}... ({elapsed}s, poll #{poll_count})")
                    
                    if status_enum in ["finished", "blocked", "stopped"]:
                        break
                    
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    # Network issue - log and continue polling
                    progress.update(task, description=f"[yellow]Connection issue, retrying... ({elapsed}s, poll #{poll_count})[/yellow]")
                    continue
                except httpx.HTTPStatusError as e:
                    console.print(f"[red]✗[/red] HTTP Error {e.response.status_code}: {e.response.text}")
                    raise typer.Exit(1)
                
                if elapsed > 1800:  # 30 minutes timeout
                    timed_out = True
                    break
        
        elapsed = int(time.time() - start_time)
        
        # Handle timeout gracefully
        if timed_out:
            console.print(f"\n[yellow]⏱️  Polling timeout after {elapsed // 60} minutes.[/yellow]")
            console.print(f"[dim]Devin is still working on this issue in the background.[/dim]\n")
            console.print(f"[bold cyan]Check progress at:[/bold cyan]")
            console.print(f"  [dim]•[/dim] Session: {session_url or session_id}")
            console.print(f"  [dim]•[/dim] GitHub issue comments will be updated automatically")
            console.print(f"  [dim]•[/dim] Re-run this command later to check status\n")
            return
        
        # Get final results (increased timeout)
        try:
            with httpx.Client(timeout=90.0) as client:
                final_response = client.get(
                    f"{orchestrator_url}/api/v1/sessions/{session_id}"
                )
                final_response.raise_for_status()
                final_data = final_response.json()
        except Exception as e:
            console.print(f"\n[yellow]⚠️  Could not fetch final results: {str(e)}[/yellow]")
            console.print(f"[dim]Check session at: {session_url or session_id}[/dim]\n")
            return
        
        structured_output = final_data.get("structured_output") or {}
        status_enum = final_data.get("status_enum", "").lower()
        
        # Determine completion message
        if status_enum == "finished":
            console.print(f"\n[bold green]✓ Execution complete![/bold green] (took {elapsed // 60}m {elapsed % 60}s)\n")
        elif status_enum == "blocked":
            console.print(f"\n[bold yellow]⚠️  Devin is blocked[/bold yellow] (after {elapsed // 60}m {elapsed % 60}s)\n")
            console.print("[dim]Devin may need input or encountered an issue. Check the session.[/dim]\n")
        else:
            console.print(f"\n[bold cyan]Session Status: {status_enum}[/bold cyan] (after {elapsed // 60}m {elapsed % 60}s)\n")
        
        # Display results (using simplified schema with safe defaults)
        if structured_output:
            status = structured_output.get("status", "N/A")
            branch = structured_output.get("branch", "")
            pr_url = structured_output.get("pr_url", "")
            tests_passed = structured_output.get("tests_passed", 0)
            tests_failed = structured_output.get("tests_failed", 0)
            
            console.print(f"[bold]Status:[/bold] [cyan]{status}[/cyan]")
            
            if branch:
                console.print(f"[bold]Branch:[/bold] [cyan]{branch}[/cyan]")
            
            if pr_url:
                console.print(f"[bold]Pull Request:[/bold] {pr_url}")
            
            if tests_passed > 0 or tests_failed > 0:
                console.print(f"\n[bold]Tests:[/bold] [green]{tests_passed} passed[/green], [red]{tests_failed} failed[/red]")
            
            console.print()
        else:
            console.print("[yellow]No structured output available yet.[/yellow]\n")
        
        console.print(f"[dim]Session: {session_url or session_id}[/dim]\n")
        
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]❌ HTTP Error {e.response.status_code}:[/bold red] {e.response.text}")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        console.print(f"[bold red]❌ Connection Error:[/bold red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print("[bold cyan]Devin GitHub Issues Automation CLI[/bold cyan]")
    console.print("Version: [green]0.1.0[/green]")
    console.print("Powered by Devin AI 🤖\n")


if __name__ == "__main__":
    app()
