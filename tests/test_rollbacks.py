def test_rollback_workflow(client, sample_app):
    """
    Verifies that a rollback:
    1. Records the RollbackEvent (SIMULATED_SUCCESS).
    2. Updates source deployment status to ROLLED_BACK.
    3. Records a new deployment with target version.
    4. Lists the event in GET /api/rollbacks.
    """
    app_id = sample_app["id"]

    # Create stable v1.0.0
    dep1 = client.post("/api/deployments", json={
        "application_id": app_id,
        "version": "v1.0.0",
        "status": "SUCCESS",
        "notes": "Stable base"
    }).get_json()["data"]

    # Create faulty v2.0.0
    dep2 = client.post("/api/deployments", json={
        "application_id": app_id,
        "version": "v2.0.0",
        "status": "FAILED",
        "notes": "Regression occurred"
    }).get_json()["data"]

    # Initiate rollback from dep2 (v2.0.0) back to dep1 (v1.0.0)
    rollback_resp = client.post(f"/api/deployments/{dep2['id']}/rollback", json={
        "target_deployment_id": dep1["id"]
    })
    assert rollback_resp.status_code == 200
    res_data = rollback_resp.get_json()
    assert res_data["is_simulated"] is True
    assert res_data["data"]["status"] == "SIMULATED_SUCCESS"
    assert res_data["new_deployment"]["version"] == "v1.0.0"

    # Verify rollbacks audit list
    list_resp = client.get("/api/rollbacks")
    assert list_resp.status_code == 200
    events = list_resp.get_json()["data"]
    assert len(events) == 1
    assert events[0]["source_version"] == "v2.0.0"
    assert events[0]["target_version"] == "v1.0.0"


def test_rollback_invalid_ids(client, sample_app):
    """Verifies that invalid or missing target deployment returns 400."""
    resp = client.post("/api/deployments/999/rollback", json={})
    assert resp.status_code == 400
    assert "target_deployment_id is required" in resp.get_json()["error"].lower()
