from flask import Blueprint, Response, jsonify
from backend.database import SessionLocal
from backend.services.report_service import generate_incidents_csv

reports_bp = Blueprint("reports", __name__, url_prefix="/api")


@reports_bp.route("/reports/incidents.csv", methods=["GET"])
def export_incidents_csv():
    """Generates and exports an incident report as a CSV file."""
    db = SessionLocal()
    try:
        csv_data, filename = generate_incidents_csv(db, save_to_storage=True)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate CSV report: {str(e)}"}), 500
    finally:
        db.close()
