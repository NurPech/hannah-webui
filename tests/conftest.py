import pytest

from hannah_webui.app import create_app

from tests.fake_hannah_client import FakeHannahClient


@pytest.fixture
def hannah():
    return FakeHannahClient()


@pytest.fixture
def app(hannah):
    flask_app = create_app(hannah)
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    """Trust_level 7 — a regular roomie, not an admin."""
    client.post("/login", data={"username": "claude", "password": "claude"})
    return client


@pytest.fixture
def admin_client(client):
    """Trust_level 10 — required for group/settings/user/satellite-admin routes."""
    client.post("/login", data={"username": "admin", "password": "admin"})
    return client
