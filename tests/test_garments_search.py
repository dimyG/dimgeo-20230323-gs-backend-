# default_skip = 0
# default_limit = 20


def test_search_garments(client):
    response = client.get("/search", params={"query": "shirt", "skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10



