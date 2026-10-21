def test_register_and_list_application(client):
    """Verifies registering a valid application and listing it."""
    payload = {
        "name": "Payments API",
        "base_url": "https://pay.example.com",
        "health_check_url": "https://pay.example.com/healthz",
        "expected_status_code": 200
    }
    create_resp = client.post("/api/apps", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.get_json()["data"]
    assert created_data["name"] == "Payments API"
    assert created_data["expected_status_code"] == 200

    # List apps
    list_resp = client.get("/api/apps")
    assert list_resp.status_code == 200
    apps = list_resp.get_json()["data"]
    assert len(apps) == 1
    assert apps[0]["name"] == "Payments API"


def test_register_application_invalid_inputs(client):
    """Verifies that missing or malformed inputs return 400 with descriptive errors."""
    # Empty payload
    resp = client.post("/api/apps", json={})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("name is required" in e.lower() for e in errors)
    assert any("base url is required" in e.lower() for e in errors)
    assert any("health check url is required" in e.lower() for e in errors)

    # Invalid URL scheme
    resp_invalid_url = client.post("/api/apps", json={
        "name": "Bad URL Service",
        "base_url": "ftp://example.com",
        "health_check_url": "not-a-valid-url",
        "expected_status_code": 999
    })
    assert resp_invalid_url.status_code == 400
    errs = resp_invalid_url.get_json()["errors"]
    assert any("valid http or https" in e.lower() for e in errs)
    assert any("valid http code (100-599)" in e.lower() for e in errs)


def test_register_duplicate_application_name(client, sample_app):
    """Verifies that attempting to register an app with a duplicate name returns 409 conflict."""
    payload = {
        "name": sample_app["name"],
        "base_url": "https://another.example.com",
        "health_check_url": "https://another.example.com/health",
        "expected_status_code": 200
    }
    resp = client.post("/api/apps", json=payload)
    assert resp.status_code == 409
    assert "already exists" in resp.get_json()["errors"][0]


def test_delete_application(client, sample_app):
    """Verifies deleting an existing application."""
    app_id = sample_app["id"]
    del_resp = client.delete(f"/api/apps/{app_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["success"] is True

    # Check that it's no longer found
    get_resp = client.get(f"/api/apps/{app_id}")
    assert get_resp.status_code == 404
