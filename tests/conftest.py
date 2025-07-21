"""
Test configuration and fixtures
"""

import pytest
import tempfile
import os
from catcare import create_app, db
from catcare.models import User, Case


@pytest.fixture
def app():
    """Create application for testing"""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(app, client):
    """Create authentication headers for API testing"""
    with app.app_context():
        # Create test user
        user = User(username="testuser", email="test@example.com")
        user.set_password("testpass123")
        db.session.add(user)
        db.session.commit()

        # Login and get token
        response = client.post(
            "/api/v1/login", json={"username": "testuser", "password": "testpass123"}
        )
        
        # Debug: print response to see actual format
        response_data = response.get_json()
        if response.status_code != 200 or not response_data.get("success"):
            pytest.fail(f"Login failed: {response_data}")

        token = response_data["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    with app.app_context():
        user = User(username="sampleuser", email="sample@example.com")
        user.set_password("samplepass123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id  # Get the ID before session closes
        db.session.expunge(user)  # Remove from session
        user.id = user_id  # Set the ID back
        return user


@pytest.fixture
def sample_case(app, sample_user):
    """Create a sample case for testing"""
    with app.app_context():
        case = Case(
            location="Test Location", needs=["Food", "Water"], status="OPEN", user_id=sample_user.id
        )
        db.session.add(case)
        db.session.commit()
        case_id = case.id  # Get the ID before session closes
        db.session.expunge(case)  # Remove from session
        case.id = case_id  # Set the ID back
        return case
