import csv
import io
from unittest.mock import patch, MagicMock


def test_incident_csv_report_generation(client, sample_app):
    """Verifies that GET /api/reports/incidents.csv returns valid CSV format."""
    app_id = sample_app["id"]

    # Trigger a failure to generate an incident
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raw = io.BytesIO(b'Failure')

    with patch("requests.get", return_value=mock_resp):
        client.post(f"/api/apps/{app_id}/check")

    # Download CSV report
    csv_resp = client.get("/api/reports/incidents.csv")
    assert csv_resp.status_code == 200
    assert csv_resp.mimetype == "text/csv"
    assert "attachment; filename=" in csv_resp.headers["Content-Disposition"]

    content = csv_resp.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    # Check header
    header = rows[0]
    assert "Incident ID" in header
    assert "Application Name" in header
    assert "Status" in header
    assert "Failure Reason" in header

    # Check data row
    assert len(rows) >= 2
    data_row = rows[1]
    assert sample_app["name"] in data_row
    assert "OPEN" in data_row
