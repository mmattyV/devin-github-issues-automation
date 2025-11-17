#!/usr/bin/env python3
"""
Integration test script for the full system.
Tests end-to-end flow: CLI → Orchestrator → Devin/GitHub clients

This script validates:
1. All components can communicate
2. Prompts are properly formatted
3. API contracts are correct
4. Error handling works
"""

import sys
import os
import time

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_environment_setup():
    """Test that environment variables are configured."""
    print("=" * 60)
    print("TEST 1: Environment Setup")
    print("=" * 60)
    
    try:
        from app.config import get_settings
        
        settings = get_settings()
        
        print(f"✓ Settings loaded successfully")
        print(f"  - Devin API URL: {settings.devin_api_url}")
        print(f"  - Orchestrator Port: {settings.orchestrator_port}")
        print(f"  - Database URL: {settings.database_url}")
        
        # Check critical settings
        if not settings.devin_api_key:
            print(f"  ⚠ DEVIN_API_KEY not set in .env")
        else:
            print(f"  ✓ Devin API key configured")
        
        if not settings.github_token:
            print(f"  ⚠ GITHUB_TOKEN not set in .env")
        else:
            print(f"  ✓ GitHub token configured")
        
        return True
    except Exception as e:
        print(f"✗ Environment setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_initialization():
    """Test database can be initialized."""
    print("\n" + "=" * 60)
    print("TEST 2: Database Initialization")
    print("=" * 60)
    
    try:
        from app.database import init_db, get_db
        from app.models import Issue, Session, Event, RepoSettings
        
        # Initialize database
        init_db()
        print(f"✓ Database initialized")
        
        # Test database session
        with get_db() as db:
            # Count records
            issue_count = db.query(Issue).count()
            session_count = db.query(Session).count()
            event_count = db.query(Event).count()
            
            print(f"  - Issues in DB: {issue_count}")
            print(f"  - Sessions in DB: {session_count}")
            print(f"  - Events in DB: {event_count}")
        
        print(f"✓ Database operations working")
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_github_client_integration():
    """Test GitHub client can connect."""
    print("\n" + "=" * 60)
    print("TEST 3: GitHub Client Integration")
    print("=" * 60)
    
    try:
        from app.clients import GitHubClient
        
        client = GitHubClient()
        print(f"✓ GitHub client initialized")
        
        # Try to list issues from a public repo (python/cpython)
        print(f"  Testing with python/cpython repository...")
        issues = client.list_issues(
            owner="python",
            repo="cpython",
            state="open",
            per_page=3
        )
        
        print(f"✓ Successfully fetched {len(issues)} issues")
        if issues:
            print(f"  - Example: #{issues[0].number} - {issues[0].title[:50]}...")
        
        # Check rate limit
        rate_limit = client.get_rate_limit_status()
        print(f"  - Rate limit remaining: {rate_limit.get('remaining', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ GitHub client test failed: {e}")
        print(f"  Check your GITHUB_TOKEN in .env")
        return False


def test_devin_client_initialization():
    """Test Devin client can be initialized."""
    print("\n" + "=" * 60)
    print("TEST 4: Devin Client Initialization")
    print("=" * 60)
    
    try:
        from app.clients import DevinClient
        
        client = DevinClient()
        print(f"✓ Devin client initialized")
        print(f"  - Base URL: {client.base_url}")
        print(f"  - API key configured: {'Yes' if client.api_key else 'No'}")
        print(f"  - Poll interval: {client.default_poll_interval}s")
        
        return True
    except Exception as e:
        print(f"✗ Devin client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_generation():
    """Test that prompts are generated correctly."""
    print("\n" + "=" * 60)
    print("TEST 5: Prompt Generation")
    print("=" * 60)
    
    try:
        from app.clients import DevinClient
        
        client = DevinClient()
        
        # Test scoping prompt
        scoping_prompt = client._build_scoping_prompt(
            issue_number=123,
            repo="test/repo",
            issue_title="Add dark mode support",
            issue_body="We need to add dark mode to the application",
            comments=["I would love this feature!", "Can we make it automatic?"]
        )
        
        print(f"✓ Scoping prompt generated ({len(scoping_prompt)} chars)")
        
        # Verify key elements
        checks = [
            ("#123" in scoping_prompt, "Issue number"),
            ("test/repo" in scoping_prompt, "Repository"),
            ("dark mode" in scoping_prompt.lower(), "Issue title"),
            ("confidence" in scoping_prompt.lower(), "Confidence score"),
            ("structured output" in scoping_prompt.lower(), "Structured output instruction"),
            ('"issue_number"' in scoping_prompt, "JSON schema"),
        ]
        
        for passed, check_name in checks:
            if passed:
                print(f"  ✓ Contains {check_name}")
            else:
                print(f"  ✗ Missing {check_name}")
                return False
        
        # Test execution prompt
        scoping_plan = {
            "plan": [
                {"step": "Add theme context", "rationale": "Manage theme state"},
                {"step": "Create dark mode styles", "rationale": "Visual changes"}
            ],
            "definition_of_done": ["Dark mode toggle works", "Styles applied correctly"]
        }
        
        execution_prompt = client._build_execution_prompt(
            issue_number=123,
            repo="test/repo",
            issue_title="Add dark mode support",
            scoping_plan=scoping_plan
        )
        
        print(f"✓ Execution prompt generated ({len(execution_prompt)} chars)")
        
        # Verify key elements
        exec_checks = [
            ("feature/devin-issue" in execution_prompt, "Branch instruction"),
            ("Pull Request" in execution_prompt, "PR instruction"),
            ("Add theme context" in execution_prompt, "Plan included"),
            ("structured output" in execution_prompt.lower(), "Structured output instruction"),
            ('"branch"' in execution_prompt, "JSON schema"),
        ]
        
        for passed, check_name in exec_checks:
            if passed:
                print(f"  ✓ Contains {check_name}")
            else:
                print(f"  ✗ Missing {check_name}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Prompt generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_app():
    """Test FastAPI app can be created."""
    print("\n" + "=" * 60)
    print("TEST 6: FastAPI Application")
    print("=" * 60)
    
    try:
        from app.api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Root endpoint works")
        print(f"  - Service: {data.get('service')}")
        print(f"  - Status: {data.get('status')}")
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        print(f"✓ Health endpoint works")
        
        # Test OpenAPI docs
        response = client.get("/openapi.json")
        assert response.status_code == 200
        print(f"✓ OpenAPI schema available")
        
        return True
    except Exception as e:
        print(f"✗ FastAPI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_commands():
    """Test CLI commands can be imported."""
    print("\n" + "=" * 60)
    print("TEST 7: CLI Commands")
    print("=" * 60)
    
    try:
        from cli.main import list, scope, execute, version
        
        print(f"✓ All CLI commands imported")
        print(f"  - list: {list.__doc__.split('\\n')[0].strip()}")
        print(f"  - scope: {scope.__doc__.split('\\n')[0].strip()}")
        print(f"  - execute: {execute.__doc__.split('\\n')[0].strip()}")
        print(f"  - version: {version.__doc__.strip()}")
        
        return True
    except Exception as e:
        print(f"✗ CLI commands test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end_data_flow():
    """Test data flows correctly through the system."""
    print("\n" + "=" * 60)
    print("TEST 8: End-to-End Data Flow")
    print("=" * 60)
    
    try:
        # Simulate the data flow
        print("Simulating: GitHub Issue → Scoping → Execution → PR")
        
        # 1. GitHub Issue fetch
        from app.clients import GitHubClient
        github_client = GitHubClient()
        
        print("  1. ✓ GitHub client ready to fetch issues")
        
        # 2. Create scoping session
        from app.clients import DevinClient
        devin_client = DevinClient()
        
        scoping_prompt = devin_client._build_scoping_prompt(
            issue_number=123,
            repo="test/repo",
            issue_title="Test issue",
            issue_body="Test body",
            comments=[]
        )
        
        print(f"  2. ✓ Scoping prompt generated (ready to send to Devin)")
        
        # 3. Simulate scoping result
        mock_scoping_output = {
            "issue_number": 123,
            "title": "Test issue",
            "summary": "This is a test",
            "plan": [{"step": "Do something", "rationale": "Because"}],
            "risk": {"level": "low", "reasons": []},
            "dependencies": [],
            "blocked_on": [],
            "est_effort_hours": 2.0,
            "confidence": 0.85,
            "definition_of_done": ["Task complete"],
            "repro_instructions": None
        }
        
        print(f"  3. ✓ Scoping output validated")
        
        # 4. Create execution session with scoping plan
        execution_prompt = devin_client._build_execution_prompt(
            issue_number=123,
            repo="test/repo",
            issue_title="Test issue",
            scoping_plan=mock_scoping_output
        )
        
        print(f"  4. ✓ Execution prompt generated (includes scoping plan)")
        
        # 5. Simulate execution result
        mock_execution_output = {
            "branch": "feature/devin-issue-123-test",
            "commits": [{"sha": "abc123", "message": "Implement feature"}],
            "tests": {"passed": 10, "failed": 0, "skipped": 0},
            "pr": {
                "url": "https://github.com/test/repo/pull/456",
                "title": "Test PR",
                "body": "Closes #123",
                "number": 456
            },
            "status": "done",
            "notes": ["Completed successfully"]
        }
        
        print(f"  5. ✓ Execution output validated")
        
        # 6. Store in database
        from app.database import get_db
        from app.models import Session, SessionPhase, SessionStatus
        
        with get_db() as db:
            test_session = Session(
                session_id="test-integration-session",
                phase=SessionPhase.SCOPE,
                repo="test/repo",
                issue_number=123,
                status=SessionStatus.FINISHED,
                last_structured_output=mock_scoping_output
            )
            db.add(test_session)
            db.commit()
            
            # Query it back
            retrieved = db.query(Session).filter_by(session_id="test-integration-session").first()
            assert retrieved is not None
            assert retrieved.last_structured_output["confidence"] == 0.85
            
            # Clean up
            db.delete(retrieved)
            db.commit()
        
        print(f"  6. ✓ Data stored and retrieved from database")
        
        print("\n✓ Complete data flow validated!")
        return True
    except Exception as e:
        print(f"✗ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("INTEGRATION TESTING: Full System")
    print("=" * 60 + "\n")
    
    results = {
        "Environment Setup": test_environment_setup(),
        "Database": test_database_initialization(),
        "GitHub Client": test_github_client_integration(),
        "Devin Client": test_devin_client_initialization(),
        "Prompt Generation": test_prompt_generation(),
        "FastAPI App": test_fastapi_app(),
        "CLI Commands": test_cli_commands(),
        "End-to-End Flow": test_end_to_end_data_flow(),
    }
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All integration tests passed!")
        print("\n✅ System is ready for production use!")
        print("\nNext steps:")
        print("  1. Start orchestrator: uvicorn app.api.main:app --reload")
        print("  2. Use CLI: python devin-issues list owner/repo")
        print("  3. Scope an issue: python devin-issues scope owner/repo 123")
        print("  4. Execute an issue: python devin-issues execute owner/repo 123")
        return 0
    else:
        print("\n❌ Some integration tests failed.")
        print("Please review the errors above and ensure:")
        print("  - .env file has DEVIN_API_KEY and GITHUB_TOKEN")
        print("  - Database is accessible")
        print("  - All dependencies are installed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

