# import pytest
# from main import app


default_skip = 0
default_limit = 20


def test_search_garments(client):
    response = client.get("/search", params={"query": "shirt", "skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10


def test_search_garments_no_results(client):
    response = client.get("/search", params={"query": "nonexistent", "skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_search_garments_no_query(client):
    response = client.get("/search", params={"skip": 0, "limit": 10})
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["type"] == "value_error.missing"


def test_search_garments_no_skip_limit(client):
    response = client.get("/search", params={"query": "shirt"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= default_limit


def test_search_garments_invalid_params(client):
    response = client.get("/search", params={"query": "shirt", "skip": "invalid", "limit": "invalid"})
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["type"] == "type_error.integer"
    assert data["detail"][1]["type"] == "type_error.integer"


def test_search_garments_no_skip(client):
    response = client.get("/search", params={"query": "shirt", "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10


def test_search_garments_no_limit(client):
    response = client.get("/search", params={"query": "shirt", "skip": 0})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= default_limit


