from unittest.mock import patch, MagicMock
import io
import requests
from backend.services.health_checker import validate_url_security, SSRFValidationError


def test_successful_health_check(client, sample_app):
    """Verifies that an expected 200 response marks the health check as HEALTHY."""
    app_id = sample_app["id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raw = io.BytesIO(b'{"status": "ok"}')

    with patch("requests.get", return_value=mock_resp):
        resp = client.post(f"/api/apps/{app_id}/check")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        check = data["check"]
        assert check["status"] == "HEALTHY"
        assert check["http_status_code"] == 200
        assert check["response_time_ms"] is not None
        assert check["error_message"] is None


def test_failed_health_check_unexpected_status(client, sample_app):
    """Verifies that an unexpected HTTP status marks check as UNHEALTHY."""
    app_id = sample_app["id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.raw = io.BytesIO(b'Service Unavailable')

    with patch("requests.get", return_value=mock_resp):
        resp = client.post(f"/api/apps/{app_id}/check")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        check = data["check"]
        assert check["status"] == "UNHEALTHY"
        assert check["http_status_code"] == 503
        assert "Expected HTTP status 200, but received 503" in check["error_message"]


def test_failed_health_check_timeout(client, sample_app):
    """Verifies that request timeouts are caught safely and marked UNHEALTHY."""
    app_id = sample_app["id"]

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        resp = client.post(f"/api/apps/{app_id}/check")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        check = data["check"]
        assert check["status"] == "UNHEALTHY"
        assert check["http_status_code"] is None
        assert "timed out" in check["error_message"].lower()


def test_ssrf_protection_blocks_localhost_and_metadata():
    """Verifies SSRF defense strictly blocks localhost, loopback, and AWS metadata addresses."""
    # Localhost
    try:
        validate_url_security("http://localhost:8080/health", allow_local=False)
        assert False, "Should have raised SSRFValidationError"
    except SSRFValidationError as e:
        assert "localhost" in str(e).lower()

    # Loopback IP
    try:
        validate_url_security("http://127.0.0.1:8080/metrics", allow_local=False)
        assert False, "Should have raised SSRFValidationError"
    except SSRFValidationError as e:
        assert "localhost/loopback" in str(e).lower()

    # AWS Cloud Metadata IP
    try:
        validate_url_security("http://169.254.169.254/latest/meta-data/", allow_local=False)
        assert False, "Should have raised SSRFValidationError"
    except SSRFValidationError as e:
        assert "cloud metadata" in str(e).lower() or "blocked for security" in str(e).lower()
