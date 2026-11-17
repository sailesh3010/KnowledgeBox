import os
import pytest
from fastapi.testclient import TestClient

# Create a fixed temporary file for tests
TEST_DB_FILE = os.path.abspath("test_knowledge_inbox.db")
os.environ["DATABASE_PATH"] = TEST_DB_FILE
os.environ["AI_PROVIDER"] = "local"

from app.main import create_app
from app.db.database import Database
import app.db.database as db_module
import app.main as main_module
import app.api.routes as routes_module
import app.services.vector_store as vs_module


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture(scope="function")
def test_db():
    """Provides a fresh isolated SQLite database for each test function."""
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

    test_database = Database(db_path=TEST_DB_FILE)

    # Inject test database instance
    db_module.db = test_database
    main_module.db = test_database
    routes_module.db = test_database
    vs_module.db = test_database
    vs_module.vector_store.db = test_database

    yield test_database


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI TestClient with isolated test database."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
