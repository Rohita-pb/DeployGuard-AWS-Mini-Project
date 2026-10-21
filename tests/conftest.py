import pytest
from backend.app import create_app
from backend.config import TestConfig
from backend.database import SessionLocal, Base, get_engine


@pytest.fixture(scope="function")
def app():
    """Creates a fresh test application with an in-memory SQLite database."""
    test_app = create_app(config_class=TestConfig)
    test_app.config["TESTING"] = True

    engine = get_engine()
    with test_app.app_context():
        # Clear and recreate tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield test_app
        SessionLocal.remove()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture(scope="function")
def sample_app(client):
    """Creates and returns a sample application for testing dependent workflows."""
    resp = client.post("/api/apps", json={
        "name": "Auth Service",
        "base_url": "https://auth.example.com",
        "health_check_url": "https://auth.example.com/health",
        "expected_status_code": 200
    })
    assert resp.status_code == 201
    return resp.get_json()["data"]
