import urllib.request
import json
import pytest


def is_live_server_running(url="http://127.0.0.1:5000/api/health"):
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def test_live_server():
    """
    End-to-end integration test executed against an actively running DeployGuard server.
    Skipped automatically during offline test runs if the live server is not running.
    """
    if not is_live_server_running():
        pytest.skip("Live server is not running on http://127.0.0.1:5000. Start it with 'python run.py' to run live tests.")

    base_url = "http://127.0.0.1:5000"

    # 1. Health
    with urllib.request.urlopen(f"{base_url}/api/health") as resp:
        health_data = json.loads(resp.read().decode())
        print("HEALTH:", health_data)
        assert health_data["status"] == "UP"

    # 2. Register App
    register_payload = json.dumps({
        "name": "Live Payment Gateway Test",
        "base_url": "https://httpbin.org",
        "health_check_url": "https://httpbin.org/status/200",
        "expected_status_code": 200
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/api/apps",
        data=register_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        app_json = json.loads(resp.read().decode())
        app = app_json["data"]
        app_id = app["id"]
        print(f"REGISTERED APP: {app['name']} (ID: {app_id})")

    # 3. Trigger Health Check
    req_check = urllib.request.Request(
        f"{base_url}/api/apps/{app_id}/check",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_check) as resp:
        check_json = json.loads(resp.read().decode())["data"]
        check = check_json["check"]
        print(f"HEALTH CHECK: Status={check['status']}, Code={check['http_status_code']}, Latency={check['response_time_ms']}ms")

    # 4. Record Deployments
    def record_deploy(ver, status, notes):
        p = json.dumps({
            "application_id": app_id,
            "version": ver,
            "status": status,
            "notes": notes
        }).encode()
        r = urllib.request.Request(f"{base_url}/api/deployments", data=p, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(r) as res:
            return json.loads(res.read().decode())["data"]

    dep1 = record_deploy("v1.0.0", "SUCCESS", "Initial stable release")
    dep2 = record_deploy("v1.1.0", "FAILED", "Regression with error spikes")
    print(f"RECORDED DEPLOYMENTS: #{dep1['id']} ({dep1['version']}) & #{dep2['id']} ({dep2['version']})")

    # 5. Initiate Rollback
    rb_payload = json.dumps({"target_deployment_id": dep1["id"]}).encode()
    req_rb = urllib.request.Request(
        f"{base_url}/api/deployments/{dep2['id']}/rollback",
        data=rb_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_rb) as resp:
        rb_json = json.loads(resp.read().decode())
        print(f"ROLLBACK STATUS: {rb_json['data']['status']}, Message: {rb_json['message']}")

    # 6. Dashboard metrics
    with urllib.request.urlopen(f"{base_url}/api/dashboard") as resp:
        dash_data = json.loads(resp.read().decode())["data"]
        print("DASHBOARD METRICS:", dash_data)

    # 7. CSV Export
    with urllib.request.urlopen(f"{base_url}/api/reports/incidents.csv") as resp:
        csv_content = resp.read().decode()
        print(f"CSV EXPORTED successfully ({len(csv_content)} bytes)")


if __name__ == "__main__":
    test_live_server()
