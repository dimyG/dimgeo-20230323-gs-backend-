import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    # When you need your event handlers (startup and shutdown) to run in your tests,
    # you can use the TestClient with a with statement
    with TestClient(app) as client:
        yield client  # yield instead of return so that the event loop is not closed
