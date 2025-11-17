# 🚀 Quick Start Guide

Get up and running with Devin GitHub Issues Automation in 5 minutes!

## Prerequisites

- Python 3.11+
- Conda (or venv)
- GitHub Personal Access Token
- Devin API Key

## Installation

### 1. Clone and Setup

```bash
cd devin-github-issues-automation
conda create -n devin-automation python=3.11 -y
conda activate devin-automation
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# Copy from example
cp .env.example .env

# Edit with your credentials
nano .env
```

Add your keys:
```
DEVIN_API_KEY=your_devin_api_key_here
GITHUB_TOKEN=your_github_token_here
```

### 3. Initialize Database

```bash
python -c "from app.database import init_db; init_db()"
```

## Usage

### Start the Orchestrator

In terminal 1:
```bash
conda activate devin-automation
uvicorn app.api.main:app --reload
```

Visit http://localhost:8000/docs to see the API documentation.

### Use the CLI

In terminal 2:

```bash
conda activate devin-automation

# List issues
python devin-issues list python/cpython --label bug --state open

# Scope an issue
python devin-issues scope owner/repo 123

# Execute an issue
python devin-issues execute owner/repo 123
```

## Your First Automation

Let's automate a real issue!

### 1. Find an Issue

```bash
python devin-issues list your-org/your-repo --state open
```

Pick an issue number (e.g., #42).

### 2. Scope It

```bash
python devin-issues scope your-org/your-repo 42
```

Devin will analyze the issue and give you:
- ✅ Implementation plan
- ✅ Confidence score
- ✅ Risk assessment
- ✅ Effort estimate

### 3. Execute It

If confidence score is good (>70%):

```bash
python devin-issues execute your-org/your-repo 42
```

Devin will:
1. Create a feature branch
2. Implement the changes
3. Run tests
4. Open a Pull Request
5. Comment on the issue with updates

## What's Happening?

### Behind the Scenes

```
CLI (your terminal)
    ↓
Orchestrator (FastAPI server at :8000)
    ↓           ↓
Devin API    GitHub API
    ↓           ↓
Your Repo + Issue → Devin works → Opens PR
```

### Data Flow

1. **CLI** sends request to Orchestrator
2. **Orchestrator** fetches issue from GitHub
3. **Orchestrator** creates Devin session with prompt
4. **Devin** analyzes/implements the issue
5. **Devin** opens PR on GitHub
6. **Orchestrator** stores session data in DB
7. **CLI** shows you the results

## Monitoring Progress

### View Session in Browser

When you run `scope` or `execute`, you'll see a session URL:
```
View session: https://preview.devin.ai/sessions/abc123...
```

Click it to watch Devin work in real-time!

### Check via API

```bash
curl http://localhost:8000/api/v1/sessions/YOUR_SESSION_ID
```

### Check via Database

```bash
sqlite3 devin_orchestrator.db "SELECT * FROM sessions;"
```

## Common Workflows

### Workflow 1: Triage Multiple Issues

```bash
# List all bugs
python devin-issues list myorg/myrepo --label bug

# Scope them all (in parallel)
for i in 42 43 44 45; do
  python devin-issues scope myorg/myrepo $i --no-wait &
done

# Wait and check confidence scores
# Execute the high-confidence ones
```

### Workflow 2: Auto-execute High Confidence

```bash
# Scope first
python devin-issues scope myorg/myrepo 42

# If confidence > 80%, auto-execute
python devin-issues execute myorg/myrepo 42
```

### Workflow 3: Batch Processing

```python
# Create a script: process_issues.py
from app.clients import GitHubClient, DevinClient
from app.database import get_db
from app.models import Issue

github = GitHubClient()
devin = DevinClient()

# Get all open bugs
issues = github.list_issues("myorg", "myrepo", label="bug")

for issue in issues:
    # Scope each one
    session = devin.create_scoping_session(
        issue_number=issue.number,
        repo="myorg/myrepo",
        issue_title=issue.title,
        issue_body=issue.body or "",
        comments=[]
    )
    print(f"Scoping #{issue.number}: {session.session_id}")
```

## Troubleshooting

### Orchestrator won't start

```bash
# Check if port 8000 is in use
lsof -i :8000

# Use a different port
ORCHESTRATOR_PORT=8001 uvicorn app.api.main:app --port 8001
```

### CLI can't connect to orchestrator

```bash
# Specify orchestrator URL
python devin-issues list myorg/myrepo --url http://localhost:8001
```

### GitHub rate limit exceeded

```bash
# Check your rate limit
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

Wait or use a different token with higher limits.

### Devin session stuck

Sessions auto-timeout after 30 minutes. If stuck:

```bash
# Check status
curl http://localhost:8000/api/v1/sessions/YOUR_SESSION_ID

# It may be "blocked" - check the session URL to see what Devin needs
```

## Next Steps

- 📖 Read the full [README.md](README.md) for architecture details
- 🔧 See [DEVIN_API_NOTES.md](DEVIN_API_NOTES.md) for API implementation notes
- 🎯 Check out the [design doc](DESIGN_DOC.md) for the full vision
- 🚀 Start automating your issues!

## Need Help?

- **API Docs**: http://localhost:8000/docs
- **GitHub Issues**: Check the repo issues
- **Devin Docs**: https://docs.devin.ai/

Happy automating! 🤖

