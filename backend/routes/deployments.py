from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from backend.database import SessionLocal
from backend.models import Application, Deployment

deployments_bp = Blueprint("deployments", __name__, url_prefix="/api")


@deployments_bp.route("/deployments", methods=["GET"])
def list_deployments():
    """Lists all recorded deployments, newest first."""
    db = SessionLocal()
    try:
        app_id = request.args.get("application_id", type=int)
        query = db.query(Deployment).order_by(Deployment.created_at.desc())
        if app_id:
            query = query.filter(Deployment.application_id == app_id)

        deployments = query.all()
        return jsonify({"success": True, "data": [d.to_dict() for d in deployments]}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to list deployments: {str(e)}"}), 500
    finally:
        db.close()


@deployments_bp.route("/deployments", methods=["POST"])
def record_deployment():
    """
    Manually records a deployment event for an application.
    Note: As noted in documentation, this records manual deployment events
    for the MVP rather than an automated CI/CD pipeline listener.
    """
    data = request.get_json(silent=True) or {}
    app_id = data.get("application_id")
    version = data.get("version", "").strip() if isinstance(data.get("version"), str) else ""
    status = data.get("status", "SUCCESS").upper().strip()
    notes = data.get("notes", "").strip() if isinstance(data.get("notes"), str) else None

    errors = []
    if not app_id:
        errors.append("application_id is required.")
    if not version:
        errors.append("version or release identifier is required.")
    elif len(version) > 50:
        errors.append("version must not exceed 50 characters.")

    valid_statuses = ("SUCCESS", "FAILED", "PENDING", "ROLLED_BACK")
    if status not in valid_statuses:
        errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}")

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return jsonify({"success": False, "error": f"Application with ID {app_id} not found."}), 404

        deployment = Deployment(
            application_id=app.id,
            version=version,
            status=status,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)

        return jsonify({
            "success": True,
            "message": "Deployment recorded successfully.",
            "data": deployment.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Failed to record deployment: {str(e)}"}), 500
    finally:
        db.close()
