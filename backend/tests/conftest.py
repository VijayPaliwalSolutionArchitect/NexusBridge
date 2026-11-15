"""Pytest fixtures.

The whole API talks to a single SQLite database chosen at import time via
``NEXUSBRIDGE_DB_PATH``.  We point that at a fresh temp file *before* the
``app`` package is imported so tests never touch the developer database and
each run starts from a clean, seeded state.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make the ``app`` package importable from anywhere pytest runs.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Use an isolated, throwaway database for every test session.
_tmpdb = Path(tempfile.mkdtemp(prefix="nexusbridge-test-")) / "nexusbridge.db"
os.environ["NEXUSBRIDGE_DB_PATH"] = str(_tmpdb)
os.environ["NEXUSBRIDGE_DATA_DIR"] = str(_tmpdb.parent)


_test_client = None


def pytest_configure() -> None:
    global _test_client
    from fastapi.testclient import TestClient

    from app import main

    _test_client = TestClient(main.app)


@pytest.fixture()
def client():
    """A FastAPI TestClient bound to the isolated application."""
    assert _test_client is not None, "pytest_configure did not run"
    return _test_client


@pytest.fixture()
def db_path():
    """Absolute path of the isolated database used by this test run."""
    return _tmpdb