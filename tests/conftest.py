"""
Pytest fixtures for forge-backend tests.
"""
import os
import tempfile
import sqlite3
import glob
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient


def _apply_migrations(db_path: str) -> None:
    """Apply database migrations to the given database path."""
    mig_dir = os.environ.get("FORGE_MIGRATIONS_DIR", "scripts/db/migrations")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        conn.commit()
        for path in sorted(glob.glob(os.path.join(mig_dir, "*.sql"))):
            mig_id = os.path.basename(path)
            cur.execute("SELECT 1 FROM schema_migrations WHERE id = ?", (mig_id,))
            if cur.fetchone():
                continue
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
            cur.executescript(sql)
            cur.execute("INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))", (mig_id,))
            conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="function")
def test_db_path() -> Generator[str, None, None]:
    """
    Provide a temporary database path for tests with migrations applied.
    Each test gets a fresh database.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Ensure DB is clean
    if os.path.exists(db_path):
        os.unlink(db_path)

    # Apply migrations
    _apply_migrations(db_path)

    # Set environment variable for the app to use
    old_db_path = os.environ.get("FORGE_DB_PATH")
    os.environ["FORGE_DB_PATH"] = db_path

    yield db_path

    # Restore environment
    if old_db_path:
        os.environ["FORGE_DB_PATH"] = old_db_path
    else:
        os.environ.pop("FORGE_DB_PATH", None)

    # Cleanup
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except:
            pass


@pytest.fixture(scope="function")
def test_db(test_db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a fresh database connection with migrations applied.
    """
    # Set environment variable for the app to use
    old_db_path = os.environ.get("FORGE_DB_PATH")
    os.environ["FORGE_DB_PATH"] = test_db_path

    # Apply migrations manually
    _apply_migrations(test_db_path)

    # Provide connection
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()

    # Restore environment
    if old_db_path:
        os.environ["FORGE_DB_PATH"] = old_db_path
    else:
        os.environ.pop("FORGE_DB_PATH", None)


@pytest.fixture(scope="function")
def test_app(test_db_path: str):
    """
    Provide a TestClient for the FastAPI app with a test database.
    """
    # Set environment variables
    old_db_path = os.environ.get("FORGE_DB_PATH")
    old_admin_token = os.environ.get("ADMIN_TOKEN")
    old_worker_enabled = os.environ.get("AUTONOMY_V2_WORKER_ENABLED")

    os.environ["FORGE_DB_PATH"] = test_db_path
    os.environ["ADMIN_TOKEN"] = "test_admin_token"
    os.environ["AUTONOMY_V2_WORKER_ENABLED"] = "false"  # Disable background worker

    # Apply migrations
    _apply_migrations(test_db_path)

    # Import app AFTER setting environment
    from forge.app import create_app
    app = create_app()

    client = TestClient(app)

    yield client

    # Restore environment
    if old_db_path:
        os.environ["FORGE_DB_PATH"] = old_db_path
    else:
        os.environ.pop("FORGE_DB_PATH", None)

    if old_admin_token:
        os.environ["ADMIN_TOKEN"] = old_admin_token
    else:
        os.environ.pop("ADMIN_TOKEN", None)

    if old_worker_enabled:
        os.environ["AUTONOMY_V2_WORKER_ENABLED"] = old_worker_enabled
    else:
        os.environ.pop("AUTONOMY_V2_WORKER_ENABLED", None)
