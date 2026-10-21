from unittest.mock import patch, MagicMock
import io


def test_incident_creation_and_deduplication(client, sample_app):
    """
    Verifies that:
    1. A failed health check creates an OPEN incident.
    2. Consecutive failures reuse the existing OPEN incident rather than creating duplicates.
    """
    app_id = sample_app["id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raw = io.BytesIO(b'Internal Server Error')

    with patch("requests.get", return_value=mock_resp):
        # First failure -> should create incident #1
        resp1 = client.post(f"/api/apps/{app_id}/check")
        assert resp1.status_code == 200
        incident_1 = resp1.get_json()["data"]["incident"]
        assert incident_1 is not None
        assert incident_1["status"] == "OPEN"
        inc_id = incident_1["id"]

        # Second failure -> should REUSE incident #1, NOT create a second one
        resp2 = client.post(f"/api/apps/{app_id}/check")
        assert resp2.status_code == 200
        incident_2 = resp2.get_json()["data"]["incident"]
        assert incident_2 is not None
        assert incident_2["id"] == inc_id, "Consecutive failed check should reuse existing open incident"

        # Check total incidents count in system
        incidents_resp = client.get("/api/incidents")
        all_incidents = incidents_resp.get_json()["data"]
        assert len(all_incidents) == 1


def test_incident_resolution(client, sample_app):
    """Verifies that an open incident can be marked as RESOLVED."""
    app_id = sample_app["id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.raw = io.BytesIO(b'Bad Gateway')

    with patch("requests.get", return_value=mock_resp):
        check_resp = client.post(f"/api/apps/{app_id}/check")
        inc_id = check_resp.get_json()["data"]["incident"]["id"]

        # Resolve incident
        resolve_resp = client.patch(f"/api/incidents/{inc_id}/resolve")
        assert resolve_resp.status_code == 200
        resolved_data = resolve_resp.get_json()["data"]
        assert resolved_data["status"] == "RESOLVED"
        assert resolved_data["resolved_at"] is not None

        # Verify active incidents count is now 0
        dash_resp = client.get("/api/dashboard")
        assert dash_resp.get_json()["data"]["active_incidents"] == 0
