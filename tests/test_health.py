def test_backend_health_endpoint(client):
    """Verifies that GET /api/health returns 200 with status UP and connected DB."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "UP"
    assert data["database"] == "CONNECTED"
    assert "version" in data
    assert "timestamp" in data
