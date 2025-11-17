# Devin GitHub Issues Automation

A production-ready automation system that integrates **Devin AI** with **GitHub Issues** to automatically triage, scope, and execute issue fixes.

```
┌─────────────┐
│  CLI (Typer)│  ← Beautiful terminal interface
└──────┬──────┘
       │ HTTP
       ▼
┌──────────────────────┐
│  FastAPI Orchestrator│  ← Central coordination
│  (Port 8000)         │
└─────┬────────────────┘
      │
      ├──► Devin API (AI implementation)
      ├──► GitHub API (Issues, PRs, Comments)
      └──► SQLite DB (Session tracking)
```

## 🎯 What Does This Do?

This system lets you:

1. **📋 List** GitHub issues with filters and confidence scores
2. **🔍 Scope** issues - Devin analyzes and creates an implementation plan with confidence score
3. **🚀 Execute** issues - Devin implements, tests, and opens a PR automatically
4. **📊 Status** - Track all Devin sessions with flexible filtering

## ✨ Features

- **🤖 AI-Powered Scoping** - Get implementation plans, risk assessments, and confidence scores
- **⚡ Automated Execution** - Devin creates branches, implements changes, runs tests, and opens PRs
- **📊 Beautiful CLI** - Rich terminal UI with tables, progress bars, and colors
- **🔄 Session Tracking** - Database stores all sessions for auditing and analytics
- **📈 Status Monitoring** - Track all sessions with flexible filtering by repo, issue, or phase
- **🎨 Structured Output** - Simplified JSON schemas with fallback message parsing
- **📝 GitHub Integration** - Auto-posts updates and PR links to issues
- **🛡️ Production Ready** - Error handling, retries, rate limiting, graceful timeouts, logging
- **⏱️ Graceful Timeouts** - Long-running sessions handled with helpful guidance

## 🚀 Quick Start

### Install

```bash
# Create environment
conda create -n devin-automation python=3.11 -y
conda activate devin-automation

# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Add your DEVIN_API_KEY and GITHUB_TOKEN
```

### Run

```bash
# Terminal 1: Start orchestrator
uvicorn app.api.main:app --reload

# Terminal 2: Use CLI
python devin-issues list python/cpython --label bug
python devin-issues scope owner/repo 123
python devin-issues execute owner/repo 123
```

📖 **See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.**

## 📋 Commands

### `list` - List GitHub Issues

```bash
python devin-issues list owner/repo [OPTIONS]

Options:
  --label TEXT        Filter by label (e.g., 'bug', 'enhancement')
  --state TEXT        Filter by state ('open', 'closed', 'all')
  --assignee TEXT     Filter by assignee username
  --page INT          Page number (default: 1)
  --per-page INT      Results per page (default: 30)
```

**Example output:**
```
📋 Listing issues for python/cpython

#       Title                                      Labels           Confidence  Updated        
#141681 Add colour to defaults in argparse help   type-feature...  85%         2025-11-17 ...
#141679 Improve error message for invalid regex   type-bug         92%         2025-11-17 ...
```

### `scope` - Scope an Issue

```bash
python devin-issues scope owner/repo ISSUE_NUMBER [OPTIONS]

Options:
  --wait / --no-wait  Wait for scoping to complete (default: --wait)
  --url TEXT          Orchestrator URL (default: http://localhost:8000)
```

**What you get:**
- ✅ Implementation plan (3-7 steps with rationale)
- ✅ Confidence score (0-100%)
- ✅ Risk assessment (low/medium/high)
- ✅ Estimated effort in hours
- ✅ Dependencies and blockers
- ✅ Definition of done (acceptance criteria)

**Example output:**
```
🔍 Scoping issue owner/repo#123

✓ Session created: abc123...
View session: https://preview.devin.ai/sessions/abc123...

Waiting for Devin to complete scoping...
(This may take 2-5 minutes)

✓ Scoping complete! (took 187s)

┌─ Summary ─────────────────────────────────────────────┐
│ Add dark mode support with toggle and persistence     │
└───────────────────────────────────────────────────────┘

Confidence Score: 85%
Estimated Effort: 3.5 hours
Risk Level: LOW

📋 Implementation Plan:
  1. Create theme context and provider
     → Centralize theme state management
  2. Add dark mode CSS variables
     → Define color schemes for both modes
  3. Implement toggle component
     → User-facing control
  4. Add localStorage persistence
     → Remember user preference
  5. Update existing components
     → Apply theme-aware styles
```

### `execute` - Execute an Issue

```bash
python devin-issues execute owner/repo ISSUE_NUMBER [OPTIONS]

Options:
  --wait / --no-wait  Wait for execution to complete (default: --no-wait)
  --url TEXT          Orchestrator URL
```

**What happens:**
1. 🌿 Creates feature branch: `feature/devin-issue-123-add-dark-mode`
2. 💻 Implements changes following the scoped plan
3. ✅ Runs tests and linting
4. 📝 Opens PR with description and checklist
5. 💬 Posts updates to the GitHub issue

**Example output:**
```
🚀 Executing issue owner/repo#123

✓ Execution session created: xyz789...
View session: https://preview.devin.ai/sessions/xyz789...

🎉 Devin is now working on this issue!

This will take 10-30 minutes. Devin will:
  1. Create a feature branch
  2. Implement the changes
  3. Run tests and linting
  4. Open a Pull Request
  5. Post updates to the GitHub issue

Check progress at: https://preview.devin.ai/sessions/xyz789...
```

### `status` - Check Session Status

```bash
python devin-issues status [SESSION_ID] [OPTIONS]

Options:
  --repo, -r TEXT     Filter by repository (owner/name)
  --issue, -i INT     Filter by issue number (requires --repo)
  --phase, -p TEXT    Filter by phase ('scope' or 'exec')
  --limit, -l INT     Maximum sessions to show (default: 20)
```

**List all sessions:**
```bash
python devin-issues status

# Output:
                    Recent Sessions (5 found)
┌──────────────────────────────────┬─────────────┬───────┬───────┬──────────┬─────────────┐
│ Session ID                       │ Repo        │ Issue │ Phase │  Status  │  Created    │
├──────────────────────────────────┼─────────────┼───────┼───────┼──────────┼─────────────┤
│ devin-abc123...                  │ owner/repo  │   #5  │ exec  │ finished │ 11/17 14:30 │
│ devin-def456...                  │ owner/repo  │   #4  │ scope │ running  │ 11/17 13:15 │
└──────────────────────────────────┴─────────────┴───────┴───────┴──────────┴─────────────┘
```

**Check specific session:**
```bash
python devin-issues status devin-abc123def456

# Output:
Session ID: devin-abc123def456
Title: Execute Issue #5: Add admin dashboard
Status: finished
Created: 2025-11-17T14:30:15+00:00
URL: https://app.devin.ai/sessions/abc123def456

Structured Output:
{
  "status": "done",
  "branch": "feature-issue-5-admin-dashboard",
  "pr_url": "https://github.com/owner/repo/pull/12",
  "tests_passed": 15,
  "tests_failed": 0
}
```

**Filter examples:**
```bash
# Sessions for a repo
python devin-issues status -r owner/repo

# Sessions for a specific issue
python devin-issues status -r owner/repo -i 5

# Only scoping sessions
python devin-issues status -p scope

# Only execution sessions
python devin-issues status -p exec

# Last 50 sessions
python devin-issues status -l 50
```

## 🏗️ Architecture

### Components

**1. CLI (`cli/main.py`)**
- Built with Typer for beautiful terminal UX
- Rich formatting (tables, progress bars, colors)
- Communicates with orchestrator via HTTP

**2. Orchestrator (`app/api/`)**
- FastAPI REST API on port 8000
- Coordinates between Devin, GitHub, and Database
- Handles session lifecycle and polling
- Auto-generates OpenAPI docs at `/docs`

**3. Clients (`app/clients/`)**
- **DevinClient**: Manages Devin AI sessions
  - Creates scoping/execution sessions
  - Polls for completion with exponential backoff
  - Embeds simplified JSON schemas in prompts
  - Handles structured output
- **GitHubClient**: Interacts with GitHub API
  - Lists/fetches issues and comments
  - Creates comments on issues
  - Manages labels
  - Rate limit handling with retries
- **MessageParser**: Fallback structured output extraction
  - Parses JSON from Devin's markdown messages
  - Validates against schemas
  - Ensures data capture even when `structured_output` is null

**4. Database (`app/database.py`, `app/models.py`)**
- SQLite (easily upgradeable to PostgreSQL)
- Tables:
  - `issues`: GitHub issues with confidence scores
  - `sessions`: Devin session tracking
  - `events`: Audit log
  - `settings`: Per-repo configuration

**5. Schemas (`app/schemas/`)**
- Pydantic models for type safety
- `ScopingOutput`: Summary, plan (list of strings), risk_level, est_effort_hours, confidence
- `ExecutionOutput`: Status, branch, pr_url, tests_passed, tests_failed
- Simplified flat structures for better Devin reliability

### Data Flow

```
User runs CLI command
    ↓
CLI calls Orchestrator API
    ↓
Orchestrator fetches issue from GitHub
    ↓
Orchestrator creates Devin session with prompt + structured output schema
    ↓
Devin analyzes/implements issue
    ↓
Orchestrator polls Devin for updates (every 15s with exponential backoff)
    ↓
Orchestrator stores results in database
    ↓
Orchestrator posts comment on GitHub issue
    ↓
CLI displays formatted results to user
```

## 📊 Database Schema

### `issues` table
- Tracks GitHub issues with metadata
- Stores confidence scores from scoping
- Records when last scoped/executed

### `sessions` table
- Links Devin sessions to GitHub issues
- Stores phase (scope/exec), status, structured output
- Tracks session lifecycle (created → running → finished)

### `events` table
- Audit trail for all system events
- Debugging and analytics

### `settings` table
- Per-repository configuration
- Default playbooks, labels to manage, automation rules

## 🔧 Configuration

All configuration in `.env`:

```bash
# Devin API
DEVIN_API_KEY=your_key_here
DEVIN_API_URL=https://api.devin.ai/v1

# GitHub API
GITHUB_TOKEN=your_pat_here

# Orchestrator
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000
DATABASE_URL=sqlite:///./devin_orchestrator.db

# Polling
DEVIN_POLL_INTERVAL=15
DEVIN_POLL_TIMEOUT=1800
DEVIN_POLL_MAX_INTERVAL=30

# Rate Limits
GITHUB_RATE_LIMIT_BUFFER=100
```

## 🎨 Structured Output

Based on [Devin's structured output docs](https://docs.devin.ai/api-reference/structured-output), our prompts embed **simplified JSON schemas** that Devin populates. We use flat structures for better reliability.

**Scoping Output (5 fields):**
```json
{
  "summary": "Add dark mode toggle with theme persistence",
  "plan": [
    "Create theme context and provider",
    "Add dark mode CSS variables",
    "Implement toggle component",
    "Add localStorage persistence"
  ],
  "risk_level": "low",
  "est_effort_hours": 3.5,
  "confidence": 0.85
}
```

**Execution Output (5 fields):**
```json
{
  "status": "done",
  "branch": "feature-issue-123-add-dark-mode",
  "pr_url": "https://github.com/owner/repo/pull/456",
  "tests_passed": 12,
  "tests_failed": 0
}
```

**Fallback Mechanism:**
- If `structured_output` is null, we parse JSON from Devin's messages
- Extracts structured data from markdown code blocks
- Validates against schema for reliability

## 🔐 Security

- ✅ API keys in `.env` (gitignored)
- ✅ Fine-grained GitHub tokens with minimal scopes
- ✅ Devin secrets for sensitive repo access
- ✅ No credentials in logs or commits
- ✅ CORS configuration for production

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[INSTALL.md](INSTALL.md)** - Detailed installation guide
- **[API Docs](http://localhost:8000/docs)** - Auto-generated FastAPI docs

## 🤝 Design Principles

1. **Reliability First**
   - Idempotent operations
   - Exponential backoff retries
   - Comprehensive error handling

2. **Observability**
   - Structured logging
   - Event audit trail
   - Session tracking in database

3. **Type Safety**
   - Pydantic schemas everywhere
   - Runtime validation
   - Auto-generated API docs

4. **Production Ready**
   - Rate limiting
   - Timeout handling
   - Database migrations support (Alembic)

## 🔄 Workflow Examples

### High-Confidence Auto-Execute

```bash
# Scope first
RESULT=$(python devin-issues scope myorg/myrepo 42 2>&1)

# Parse confidence
CONFIDENCE=$(echo "$RESULT" | grep "Confidence:" | awk '{print $3}')

# Auto-execute if > 80%
if [ "$CONFIDENCE" -gt "80" ]; then
  python devin-issues execute myorg/myrepo 42
fi
```

### Batch Triage

```python
from app.clients import GitHubClient, DevinClient

github = GitHubClient()
devin = DevinClient()

# Get all bugs
issues = github.list_issues("myorg", "myrepo", label="bug")

for issue in issues:
    session = devin.create_scoping_session(
        issue_number=issue.number,
        repo="myorg/myrepo",
        issue_title=issue.title,
        issue_body=issue.body or "",
        comments=[]
    )
    print(f"Scoping #{issue.number}: {session.session_id}")
```

## 🎯 Roadmap

- [ ] GitHub App support (instead of PAT)
- [ ] Webhook integration for auto-triage
- [ ] Confidence calibration with historical data
- [ ] Multi-repo dashboard
- [ ] Slack notifications
- [ ] Auto-merge for high-confidence fixes
- [ ] Playbook management UI

## 📄 License

See [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- **Devin AI** by Cognition for the amazing AI engineer
- **FastAPI** for the excellent web framework
- **Typer** + **Rich** for beautiful CLI UX
- **Cognition's qa-devin** example for API best practices

---

**Built with ❤️ using FastAPI, Typer, SQLAlchemy, HTTPX, Rich, and Pydantic**

🤖 **Start automating your GitHub issues today!**
