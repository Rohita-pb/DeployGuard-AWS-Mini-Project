from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models import Incident, Application
from backend.services.notification_service import send_incident_notification


def handle_check_result(db: Session, app: Application, check_result: dict):
    """
    Evaluates health check result. If UNHEALTHY, creates an incident or reuses
    an existing OPEN incident to avoid duplicate alarms.
    """
    if check_result.get("status") != "UNHEALTHY":
        return None

    # Check for existing OPEN incident for this application
    existing_incident = (
        db.query(Incident)
        .filter(Incident.application_id == app.id, Incident.status == "OPEN")
        .first()
    )

    reason = check_result.get("error_message") or "Application health check failed unexpectedly."

    if existing_incident:
        # Avoid creating duplicate consecutive incidents
        return existing_incident

    # Create new Incident
    new_incident = Incident(
        application_id=app.id,
        reason=reason,
        status="OPEN",
        opened_at=datetime.now(timezone.utc),
    )
    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    # Trigger notification (SNS or local logger)
    try:
        send_incident_notification(app, new_incident)
    except Exception as e:
        # Logging notification error should not crash the transaction
        print(f"[Warning] Failed to send incident notification: {e}")

    return new_incident


def resolve_incident(db: Session, incident_id: int):
    """
    Marks an open incident as RESOLVED.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return None

    if incident.status != "RESOLVED":
        incident.status = "RESOLVED"
        incident.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(incident)

    return incident
