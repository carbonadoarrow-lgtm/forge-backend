"""
D.12-A Read-Only Operational Ergonomics Endpoints Tests

Tests for:
- GET /api/autonomy/v2/runs (list with pagination)
- GET /api/autonomy/v2/runs/{run_id} (get detail)
- GET /api/autonomy/v2/runs/{run_id}/events (get events with pagination)
"""
import pytest
import sqlite3
import json
from contextlib import contextmanager


@contextmanager
def mock_get_db(db_path):
    """Context manager for database connection."""
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.mark.acceptance
def test_list_runs_empty(test_db_path):
    """Test listing runs when database is empty."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    from forge.autonomy.api_v2 import list_runs
    from unittest.mock import Mock

    # Mock request with get_db
    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Call endpoint
    import asyncio
    result = asyncio.run(list_runs(request=request))

    assert result["items"] == []
    assert result["next_cursor"] is None


@pytest.mark.acceptance
def test_list_runs_with_data(test_db_path):
    """Test listing runs with actual data."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    # Insert test runs
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()

    # Create 3 test runs
    for i in range(3):
        cur.execute(
            """
            INSERT INTO runs_v2 (run_id, schema_version, status, env, lane, mode, job_type, requested_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"run_{i}",
                "v2",
                "pending" if i == 0 else "running",
                "local",
                "default",
                "dry_run",
                "autobuilder",
                "test_user",
                f"2025-01-0{i+1}T10:00:00Z"
            )
        )
    conn.commit()
    conn.close()

    from forge.autonomy.api_v2 import list_runs
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Call endpoint
    import asyncio
    result = asyncio.run(list_runs(request=request))

    assert len(result["items"]) == 3
    # Should be ordered by created_at DESC
    assert result["items"][0]["run_id"] == "run_2"
    assert result["items"][1]["run_id"] == "run_1"
    assert result["items"][2]["run_id"] == "run_0"
    assert result["next_cursor"] is None


@pytest.mark.acceptance
def test_list_runs_pagination(test_db_path):
    """Test runs list pagination with cursor."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    # Insert 5 test runs
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()

    for i in range(5):
        cur.execute(
            """
            INSERT INTO runs_v2 (run_id, schema_version, status, env, lane, mode, job_type, requested_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"run_{i}",
                "v2",
                "pending",
                "local",
                "default",
                "dry_run",
                "autobuilder",
                "test_user",
                f"2025-01-0{i+1}T10:00:00Z"
            )
        )
    conn.commit()
    conn.close()

    from forge.autonomy.api_v2 import list_runs
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Get first page (limit 2)
    import asyncio
    result = asyncio.run(list_runs(request=request, limit=2))

    assert len(result["items"]) == 2
    assert result["items"][0]["run_id"] == "run_4"  # newest first
    assert result["items"][1]["run_id"] == "run_3"
    assert result["next_cursor"] is not None

    # Get second page using cursor
    result2 = asyncio.run(list_runs(request=request, limit=2, cursor=result["next_cursor"]))

    assert len(result2["items"]) == 2
    assert result2["items"][0]["run_id"] == "run_2"
    assert result2["items"][1]["run_id"] == "run_1"
    assert result2["next_cursor"] is not None


@pytest.mark.acceptance
def test_list_runs_filter_by_status(test_db_path):
    """Test filtering runs by status."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    # Insert runs with different statuses
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()

    statuses = ["pending", "running", "succeeded", "failed"]
    for i, status in enumerate(statuses):
        cur.execute(
            """
            INSERT INTO runs_v2 (run_id, schema_version, status, env, lane, mode, job_type, requested_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"run_{i}",
                "v2",
                status,
                "local",
                "default",
                "dry_run",
                "autobuilder",
                "test_user",
                f"2025-01-0{i+1}T10:00:00Z"
            )
        )
    conn.commit()
    conn.close()

    from forge.autonomy.api_v2 import list_runs
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Filter by status=succeeded
    import asyncio
    result = asyncio.run(list_runs(request=request, status="succeeded"))

    assert len(result["items"]) == 1
    assert result["items"][0]["status"] == "succeeded"


@pytest.mark.acceptance
def test_get_run_success(test_db_path):
    """Test getting a run by ID."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    # Insert test run
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO runs_v2 (run_id, schema_version, status, env, lane, mode, job_type, requested_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "test_run_123",
            "v2",
            "succeeded",
            "prod",
            "main",
            "real_run",
            "deployer",
            "alice",
            "2025-01-15T14:30:00Z"
        )
    )
    conn.commit()
    conn.close()

    from forge.autonomy.api_v2 import get_run
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Get run
    import asyncio
    result = asyncio.run(get_run(request=request, run_id="test_run_123"))

    assert result["run_id"] == "test_run_123"
    assert result["env"] == "prod"
    assert result["lane"] == "main"
    assert result["status"] == "succeeded"
    assert result["requested_by"] == "alice"


@pytest.mark.acceptance
def test_get_run_not_found(test_db_path):
    """Test getting a run that doesn't exist returns 404."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    from forge.autonomy.api_v2 import get_run
    from fastapi import HTTPException
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Try to get non-existent run
    import asyncio
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_run(request=request, run_id="nonexistent"))

    assert exc_info.value.status_code == 404
    assert "RUN_NOT_FOUND" in str(exc_info.value.detail)


@pytest.mark.acceptance
def test_get_run_events_success(test_db_path):
    """Test getting events for a run."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    # Insert test run and events
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO runs_v2 (run_id, schema_version, status, env, lane, mode, job_type, requested_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("test_run", "v2", "running", "local", "default", "dry_run", "autobuilder", "test", "2025-01-15T10:00:00Z")
    )

    # Add 3 events
    for i in range(3):
        cur.execute(
            """
            INSERT INTO run_events_v2 (run_id, ts, event_type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                "test_run",
                f"2025-01-15T10:0{i}:00Z",
                "step_started" if i == 0 else "step_completed",
                json.dumps({"step": f"step_{i}"})
            )
        )

    conn.commit()
    conn.close()

    from forge.autonomy.api_v2 import get_run_events
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Get events
    import asyncio
    result = asyncio.run(get_run_events(request=request, run_id="test_run"))

    assert len(result["items"]) == 3
    # Events should be in chronological order (ts ASC)
    assert result["items"][0]["event_type"] == "step_started"
    assert result["items"][1]["event_type"] == "step_completed"
    assert result["items"][2]["event_type"] == "step_completed"
    assert result["next_cursor"] is None


@pytest.mark.acceptance
def test_get_run_events_pagination(test_db_path):
    """Test events pagination with cursor."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    # Insert test run and 5 events
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO runs_v2 (run_id, schema_version, status, env, lane, mode, job_type, requested_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("test_run", "v2", "running", "local", "default", "dry_run", "autobuilder", "test", "2025-01-15T10:00:00Z")
    )

    for i in range(5):
        cur.execute(
            """
            INSERT INTO run_events_v2 (run_id, ts, event_type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                "test_run",
                f"2025-01-15T10:0{i}:00Z",
                "event",
                json.dumps({"index": i})
            )
        )

    conn.commit()
    conn.close()

    from forge.autonomy.api_v2 import get_run_events
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Get first page (limit 2)
    import asyncio
    result = asyncio.run(get_run_events(request=request, run_id="test_run", limit=2))

    assert len(result["items"]) == 2
    assert result["items"][0]["payload"]["index"] == 0
    assert result["items"][1]["payload"]["index"] == 1
    assert result["next_cursor"] is not None

    # Get second page using cursor
    result2 = asyncio.run(get_run_events(request=request, run_id="test_run", limit=2, cursor=result["next_cursor"]))

    assert len(result2["items"]) == 2
    assert result2["items"][0]["payload"]["index"] == 2
    assert result2["items"][1]["payload"]["index"] == 3


@pytest.mark.acceptance
def test_get_run_events_run_not_found(test_db_path):
    """Test getting events for non-existent run returns 404."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    from forge.autonomy.api_v2 import get_run_events
    from fastapi import HTTPException
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Try to get events for non-existent run
    import asyncio
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_run_events(request=request, run_id="nonexistent"))

    assert exc_info.value.status_code == 404
    assert "RUN_NOT_FOUND" in str(exc_info.value.detail)


@pytest.mark.acceptance
def test_invalid_cursor_format(test_db_path):
    """Test that invalid cursor returns 400 with INVALID_CURSOR error."""
    import os
    os.environ["FORGE_DB_PATH"] = test_db_path

    from forge.autonomy.api_v2 import list_runs
    from fastapi import HTTPException
    from unittest.mock import Mock

    request = Mock()
    request.app.state.get_db = lambda: mock_get_db(test_db_path)

    # Try with invalid cursor (missing parts)
    import asyncio
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(list_runs(request=request, cursor="invalid"))

    assert exc_info.value.status_code == 400
    assert "INVALID_CURSOR" in str(exc_info.value.detail)
