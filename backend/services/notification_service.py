import json
from datetime import datetime, timezone
from backend.config import Config


class NotificationProvider:
    """Base interface for incident notifications."""
    def send(self, subject: str, message: dict):
        raise NotImplementedError


class LocalLoggingNotificationProvider(NotificationProvider):
    """Logs notifications to standard application logger / console."""
    def send(self, subject: str, message: dict):
        now_str = datetime.now(timezone.utc).isoformat()
        print(f"[{now_str}] [NOTIFICATION: {subject}] {json.dumps(message, indent=2)}")


class SNSNotificationProvider(NotificationProvider):
    """Sends notifications to an Amazon SNS topic for alerting via SMS/Email."""
    def __init__(self, topic_arn: str, region_name: str = "us-east-1"):
        import boto3
        self.topic_arn = topic_arn
        self.sns_client = boto3.client("sns", region_name=region_name)

    def send(self, subject: str, message: dict):
        self.sns_client.publish(
            TopicArn=self.topic_arn,
            Subject=subject[:100],
            Message=json.dumps(message)
        )


def get_notification_provider() -> NotificationProvider:
    """Factory returning the active notification provider."""
    if Config.NOTIFICATION_PROVIDER == "sns" and Config.SNS_TOPIC_ARN:
        return SNSNotificationProvider(Config.SNS_TOPIC_ARN, Config.AWS_REGION)
    return LocalLoggingNotificationProvider()


def send_incident_notification(app, incident):
    """Helper to dispatch incident notifications."""
    provider = get_notification_provider()
    payload = {
        "event": "DEPLOYGUARD_INCIDENT_OPENED",
        "incident_id": incident.id,
        "application_id": app.id,
        "application_name": app.name,
        "health_check_url": app.health_check_url,
        "reason": incident.reason,
        "opened_at": incident.opened_at.isoformat() if incident.opened_at else None,
    }
    provider.send(f"[DeployGuard Alert] Incident Opened for {app.name}", payload)
