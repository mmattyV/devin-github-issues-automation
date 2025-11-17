# Installation Guide

## Quick Start

### 1. Create Virtual Environment

```bash
cd devin-github-issues-automation
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root with the following content:

```bash
# Devin API Configuration
DEVIN_API_KEY=your_devin_api_key_here
DEVIN_API_URL=https://api.devin.ai/v1

# GitHub API Configuration
GITHUB_TOKEN=your_github_personal_access_token_here

# Orchestrator Configuration
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000
DATABASE_URL=sqlite:///./devin_orchestrator.db

# Logging
LOG_LEVEL=INFO

# Polling Configuration
DEVIN_POLL_INTERVAL=15
DEVIN_POLL_TIMEOUT=1800
DEVIN_POLL_MAX_INTERVAL=30

# GitHub Rate Limiting
GITHUB_RATE_LIMIT_BUFFER=100
```

### 4. Obtain API Credentials

#### GitHub Personal Access Token (PAT)

1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Set the following scopes:
   - `repo` (Full control of private repositories)
   - `workflow` (if you need to trigger workflows)
4. Copy the token and add it to your `.env` file as `GITHUB_TOKEN`

#### Devin API Key

1. Contact Devin AI or check your Devin dashboard for API access
2. Copy your API key
3. Add it to your `.env` file as `DEVIN_API_KEY`

### 5. Initialize Database

The database will be automatically created on first run. To manually initialize:

```bash
python -c "from app.database import init_db; init_db()"
```

### 6. Start the Orchestrator

```bash
cd app
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be running at `http://localhost:8000`

### 7. Verify Installation

Open a new terminal and test the CLI:

```bash
source venv/bin/activate
python -m cli.main --help
```

You should see the CLI help with available commands: `list`, `scope`, `execute`

## Troubleshooting

### Import Errors

If you get import errors, make sure you're in the project root directory and the virtual environment is activated:

```bash
cd /path/to/devin-github-issues-automation
source venv/bin/activate
```

### Database Errors

If you encounter database errors, try deleting the database file and restarting:

```bash
rm devin_orchestrator.db
# Restart the orchestrator
```

### API Connection Errors

- Verify your `.env` file has the correct API keys
- Check that the orchestrator is running on port 8000
- Ensure no firewall is blocking the connection

### GitHub Rate Limiting

If you hit GitHub rate limits:
- Use a Personal Access Token (higher rate limits than unauthenticated)
- Wait for the rate limit to reset (check response headers)
- Implement caching for frequently accessed data

## Development Setup

For development, install additional tools:

```bash
pip install black flake8 mypy pytest pytest-cov
```

Run tests:

```bash
pytest
```

Format code:

```bash
black app/ cli/
```

Lint code:

```bash
flake8 app/ cli/
```

Type check:

```bash
mypy app/ cli/
```

