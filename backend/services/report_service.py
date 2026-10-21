import csv
import io
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models import Incident
from backend.services.storage_service import get_storage_provider


def generate_incidents_csv(db: Session, save_to_storage: bool = False) -> tuple[str, str]:
    """
    Generates a CSV report of all incidents.
    Returns a tuple: (csv_content_string, filename).
    If save_to_storage is True, also saves the report using the active StorageProvider
    (Local disk or Amazon S3).
    """
    incidents = (
        db.query(Incident)
        .order_by(Incident.opened_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Incident ID",
        "Application ID",
        "Application Name",
        "Status",
        "Failure Reason",
        "Opened At (UTC)",
        "Resolved At (UTC)",
        "Duration (Minutes)"
    ])

    for inc in incidents:
        app_name = inc.application.name if inc.application else "Unknown"
        opened_str = inc.opened_at.strftime("%Y-%m-%d %H:%M:%S") if inc.opened_at else ""
        resolved_str = inc.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if inc.resolved_at else ""
        
        duration_mins = ""
        if inc.opened_at and inc.resolved_at:
            delta = inc.resolved_at - inc.opened_at
            duration_mins = f"{round(delta.total_seconds() / 60.0, 1)}"

        writer.writerow([
            inc.id,
            inc.application_id,
            app_name,
            inc.status,
            inc.reason,
            opened_str,
            resolved_str,
            duration_mins
        ])

    csv_content = output.getvalue()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"incident_report_{timestamp}.csv"

    if save_to_storage:
        storage = get_storage_provider()
        storage.save_file(filename, csv_content)

    return csv_content, filename
