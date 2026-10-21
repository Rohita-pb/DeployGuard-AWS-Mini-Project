from flask import Blueprint, request, jsonify
from backend.database import SessionLocal
from backend.models import Incident
from backend.services.incident_service import resolve_incident

incidents_bp = Blueprint("incidents", __name__, url_prefix="/api")


@incidents_bp.route("/incidents", methods=["GET"])
def list_incidents():
    """Lists incidents with optional status filter (e.g. ?status=OPEN)."""
    db = SessionLocal()
    try:
        status_filter = request.args.get("status")
        query = db.query(Incident).order_by(Incident.opened_at.desc())

        if status_filter:
            query = query.filter(Incident.status == status_filter.upper())

        incidents = query.all()
        return jsonify({"success": True, "data": [i.to_dict() for i in incidents]}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to list incidents: {str(e)}"}), 500
    finally:
        db.close()


@incidents_bp.route("/incidents/<int:incident_id>/resolve", methods=["PATCH"])
def mark_incident_resolved(incident_id: int):
    """Marks an active incident as RESOLVED."""
    db = SessionLocal()
    try:
        incident = resolve_incident(db, incident_id)
        if not incident:
            return jsonify({"success": False, "error": f"Incident with ID {incident_id} not found."}), 404

        return jsonify({
            "success": True,
            "message": f"Incident #{incident_id} marked as RESOLVED.",
            "data": incident.to_dict()
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Failed to resolve incident: {str(e)}"}), 500
    finally:
        db.close()
