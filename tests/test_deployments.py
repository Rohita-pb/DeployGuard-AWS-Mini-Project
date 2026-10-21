def test_record_and_list_deployments(client, sample_app):
    """Verifies manually recording deployments and querying deployment history."""
    app_id = sample_app["id"]

    dep1 = client.post("/api/deployments", json={
        "application_id": app_id,
        "version": "v1.0.0",
        "status": "SUCCESS",
        "notes": "Initial release"
    })
    assert dep1.status_code == 201
    assert dep1.get_json()["data"]["version"] == "v1.0.0"

    dep2 = client.post("/api/deployments", json={
        "application_id": app_id,
        "version": "v1.1.0",
        "status": "FAILED",
        "notes": "Buggy release causing 500 errors"
    })
    assert dep2.status_code == 201

    # List deployments (latest first)
    list_resp = client.get("/api/deployments")
    assert list_resp.status_code == 200
    deps = list_resp.get_json()["data"]
    assert len(deps) == 2
    assert deps[0]["version"] == "v1.1.0"
    assert deps[1]["version"] == "v1.0.0"


def test_record_deployment_validation(client):
    """Verifies that missing application_id or version returns 400."""
    resp = client.post("/api/deployments", json={"status": "SUCCESS"})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("application_id is required" in e.lower() for e in errors)
    assert any("version" in e.lower() for e in errors)
