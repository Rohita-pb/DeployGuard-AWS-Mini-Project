from flask import Blueprint, request, jsonify
from backend.database import SessionLocal
from backend.models import RollbackEvent
from backend.services.rollback_service import initiate_rollback

rollbacks_bp = Blueprint("rollbacks", __name__, url_prefix="/api")


@rollbacks_bp.route("/rollbacks", methods=["GET"])
def list_rollbacks():
    """Lists all recorded rollback events."""
    db = SessionLocal()
    try:
        events = db.query(RollbackEvent).order_by(RollbackEvent.created_at.desc()).all()
        return jsonify({"success": True, "data": [r.to_dict() for r in events]}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to list rollbacks: {str(e)}"}), 500
    finally:
        db.close()


@rollbacks_bp.route("/deployments/<int:deployment_id>/rollback", methods=["POST"])
def trigger_rollback(deployment_id: int):
    """
    Initiates a rollback workflow from source deployment (deployment_id)
    to a designated target deployment.
    Note: In local MVP mode, this performs a clearly documented simulated rollback.
    """
    data = request.get_json(silent=True) or {}
    target_deployment_id = data.get("target_deployment_id")

    if not target_deployment_id:
        return jsonify({"success": False, "error": "target_deployment_id is required."}), 400

    db = SessionLocal()
    try:
        result = initiate_rollback(
            db=db,
            source_deployment_id=deployment_id,
            target_deployment_id=target_deployment_id
        )
        return jsonify({
            "success": True,
            "message": result["message"],
            "is_simulated": result["is_simulated"],
            "data": result["rollback_event"],
            "new_deployment": result["new_deployment"]
        }), 200
    except ValueError as ve:
        db.rollback()
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Rollback failed: {str(e)}"}), 500
    finally:
        db.close()
