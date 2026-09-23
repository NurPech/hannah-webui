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


TELEGRAM_BOT_TOKEN = "test-bot-token"


@pytest.fixture
def telegram_client(hannah):
    flask_app = create_app(hannah, telegram_bot_token=TELEGRAM_BOT_TOKEN, telegram_bot_username="SmartHomeRene_bot")
    flask_app.config.update(TESTING=True)
    c = flask_app.test_client()
    c.post("/login", data={"username": "claude", "password": "claude"})
    return c


ENTRA_TENANT = "11111111-2222-3333-4444-555555555555"


class FakeEntraApp:
    """Stand-in für msal.ConfidentialClientApplication — kein Netzwerk. `result` bzw.
    `error` steuern, was acquire_token_by_auth_code_flow() liefert."""

    def __init__(self):
        self.initiate_kwargs = None
        self.result = {"id_token_claims": {
            "oid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "tid": ENTRA_TENANT,
            "preferred_username": "claude@example.com", "name": "Claude",
        }}
        self.error = None

    def initiate_auth_code_flow(self, **kwargs):
        self.initiate_kwargs = kwargs
        return {"auth_uri": "https://login.microsoftonline.com/authorize?state=abc", "state": "abc"}

    def acquire_token_by_auth_code_flow(self, flow, auth_response):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def entra_app():
    return FakeEntraApp()


@pytest.fixture
def entra_client(hannah, entra_app):
    flask_app = create_app(hannah, entra_client_id="client-id", entra_client_secret="secret", entra_tenant=ENTRA_TENANT)
    flask_app.config.update(TESTING=True)
    flask_app.extensions["entra_msal"] = entra_app
    c = flask_app.test_client()
    c.post("/login", data={"username": "claude", "password": "claude"})
    return c
