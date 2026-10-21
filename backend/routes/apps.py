from urllib.parse import urlparse
from flask import Blueprint, request, jsonify
from backend.database import SessionLocal
from backend.models import Application, HealthCheck, Incident, Deployment

apps_bp = Blueprint("apps", __name__, url_prefix="/api")


def validate_app_payload(data: dict):
    errors = []
    name = data.get("name", "").strip() if isinstance(data.get("name"), str) else ""
    base_url = data.get("base_url", "").strip() if isinstance(data.get("base_url"), str) else ""
    health_check_url = data.get("health_check_url", "").strip() if isinstance(data.get("health_check_url"), str) else ""
    expected_status_code = data.get("expected_status_code", 200)

    if not name:
        errors.append("Application name is required.")
    elif len(name) > 100:
        errors.append("Application name must not exceed 100 characters.")

    if not base_url:
        errors.append("Base URL is required.")
    else:
        parsed_base = urlparse(base_url)
        if parsed_base.scheme not in ("http", "https") or not parsed_base.netloc:
            errors.append("Base URL must be a valid HTTP or HTTPS URL.")

    if not health_check_url:
        errors.append("Health check URL is required.")
    else:
        parsed_hc = urlparse(health_check_url)
        if parsed_hc.scheme not in ("http", "https") or not parsed_hc.netloc:
            errors.append("Health check URL must be a valid HTTP or HTTPS URL.")

    try:
        expected_status_code = int(expected_status_code)
        if expected_status_code < 100 or expected_status_code > 599:
            errors.append("Expected status code must be a valid HTTP code (100-599).")
    except (ValueError, TypeError):
        errors.append("Expected status code must be an integer.")

    return errors, {
        "name": name,
        "base_url": base_url,
        "health_check_url": health_check_url,
        "expected_status_code": expected_status_code
    }


@apps_bp.route("/dashboard", methods=["GET"])
def get_dashboard():
    """Returns real-time dashboard summary metrics."""
    db = SessionLocal()
    try:
        apps = db.query(Application).all()
        total_apps = len(apps)

        healthy_count = 0
        unhealthy_count = 0

        for app in apps:
            latest_check = (
                db.query(HealthCheck)
                .filter(HealthCheck.application_id == app.id)
                .order_by(HealthCheck.checked_at.desc())
                .first()
            )
            has_open_incident = (
                db.query(Incident)
                .filter(Incident.application_id == app.id, Incident.status == "OPEN")
                .first()
            ) is not None

            if has_open_incident or (latest_check and latest_check.status == "UNHEALTHY"):
                unhealthy_count += 1
            elif latest_check and latest_check.status == "HEALTHY":
                healthy_count += 1

        active_incidents = (
            db.query(Incident)
            .filter(Incident.status == "OPEN")
            .count()
        )

        recent_deployments_records = (
            db.query(Deployment)
            .order_by(Deployment.created_at.desc())
            .limit(5)
            .all()
        )
        recent_deployments = [d.to_dict() for d in recent_deployments_records]

        return jsonify({
            "success": True,
            "data": {
                "total_applications": total_apps,
                "healthy_applications": healthy_count,
                "unhealthy_applications": unhealthy_count,
                "active_incidents": active_incidents,
                "recent_deployments": recent_deployments
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to load dashboard: {str(e)}"}), 500
    finally:
        db.close()


@apps_bp.route("/apps", methods=["GET"])
def list_apps():
    """Lists all registered applications with current health status and response time."""
    db = SessionLocal()
    try:
        apps = db.query(Application).order_by(Application.created_at.desc()).all()
        result = [app.to_dict(include_latest_check=True) for app in apps]
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to list applications: {str(e)}"}), 500
    finally:
        db.close()


@apps_bp.route("/apps", methods=["POST"])
def register_app():
    """Registers a new application after validation."""
    data = request.get_json(silent=True) or {}
    errors, clean_data = validate_app_payload(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    db = SessionLocal()
    try:
        # Check for duplicate name
        existing = db.query(Application).filter(Application.name == clean_data["name"]).first()
        if existing:
            return jsonify({"success": False, "errors": ["An application with this name already exists."]}), 409

        app = Application(
            name=clean_data["name"],
            base_url=clean_data["base_url"],
            health_check_url=clean_data["health_check_url"],
            expected_status_code=clean_data["expected_status_code"],
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        return jsonify({
            "success": True,
            "message": "Application registered successfully.",
            "data": app.to_dict(include_latest_check=True)
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Failed to register application: {str(e)}"}), 500
    finally:
        db.close()


@apps_bp.route("/apps/<int:app_id>", methods=["GET"])
def get_app(app_id: int):
    """Retrieves single application details along with history summaries."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return jsonify({"success": False, "error": f"Application with ID {app_id} not found."}), 404

        data = app.to_dict(include_latest_check=True)
        data["recent_checks"] = [c.to_dict() for c in app.health_checks[:10]]
        data["recent_deployments"] = [d.to_dict() for d in app.deployments[:5]]
        data["open_incidents"] = [i.to_dict() for i in app.incidents if i.status == "OPEN"]
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to retrieve application: {str(e)}"}), 500
    finally:
        db.close()


@apps_bp.route("/apps/<int:app_id>", methods=["DELETE"])
def delete_app(app_id: int):
    """Deletes an application and cascading records."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return jsonify({"success": False, "error": f"Application with ID {app_id} not found."}), 404

        db.delete(app)
        db.commit()
        return jsonify({
            "success": True,
            "message": f"Application '{app.name}' and all associated records deleted successfully."
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Failed to delete application: {str(e)}"}), 500
    finally:
        db.close()
