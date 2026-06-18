import os
import sys
import tempfile
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))

# Point the app at a throwaway SQLite file before any app modules import config.
_tmp_dir = tempfile.mkdtemp()
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ["DATABASE_PATH"] = str(Path(_tmp_dir) / "test_chat_history.db")


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from api.app import app

    with TestClient(app) as test_client:
        yield test_client
