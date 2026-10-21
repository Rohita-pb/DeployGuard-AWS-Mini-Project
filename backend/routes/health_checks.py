from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from backend.database import SessionLocal
from backend.models import Application, HealthCheck
from backend.services.health_checker import perform_health_check
from backend.services.incident_service import handle_check_result

health_bp = Blueprint("health_checks", __name__, url_prefix="/api")


@health_bp.route("/apps/<int:app_id>/check", methods=["POST"])
def trigger_health_check(app_id: int):
    """
    Triggers an immediate manual health check against the application's health_check_url.
    Stores the check in the database and creates an incident if the check fails.
    """
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return jsonify({"success": False, "error": f"Application with ID {app_id} not found."}), 404

        # Execute the check
        check_result = perform_health_check(
            url=app.health_check_url,
            expected_status_code=app.expected_status_code
        )

        # Record check in database
        health_record = HealthCheck(
            application_id=app.id,
            status=check_result["status"],
            http_status_code=check_result["http_status_code"],
            response_time_ms=check_result["response_time_ms"],
            error_message=check_result["error_message"],
            checked_at=datetime.now(timezone.utc),
        )
        db.add(health_record)
        db.commit()
        db.refresh(health_record)

        # Trigger incident evaluation
        incident = handle_check_result(db, app, check_result)

        return jsonify({
            "success": True,
            "data": {
                "check": health_record.to_dict(),
                "incident": incident.to_dict() if incident else None,
                "is_incident_created": incident is not None and incident.opened_at == health_record.checked_at
            }
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Failed to execute health check: {str(e)}"}), 500
    finally:
        db.close()


@health_bp.route("/apps/<int:app_id>/checks", methods=["GET"])
def get_app_checks(app_id: int):
    """Retrieves recent health checks for a specific application."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return jsonify({"success": False, "error": f"Application with ID {app_id} not found."}), 404

        limit = request.args.get("limit", default=50, type=int)
        checks = (
            db.query(HealthCheck)
            .filter(HealthCheck.application_id == app_id)
            .order_by(HealthCheck.checked_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify({"success": True, "data": [c.to_dict() for c in checks]}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to retrieve health checks: {str(e)}"}), 500
    finally:
        db.close()


@health_bp.route("/checks", methods=["GET"])
def get_all_checks():
    """Retrieves recent health checks across all applications."""
    db = SessionLocal()
    try:
        limit = request.args.get("limit", default=50, type=int)
        checks = (
            db.query(HealthCheck)
            .order_by(HealthCheck.checked_at.desc())
            .limit(limit)
            .all()
        )
        return jsonify({"success": True, "data": [c.to_dict() for c in checks]}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to retrieve health checks: {str(e)}"}), 500
    finally:
        db.close()
