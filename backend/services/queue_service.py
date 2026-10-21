import json
from backend.config import Config


class QueueProvider:
    """Base interface for background job queuing."""
    def send_job(self, queue_name: str, payload: dict):
        raise NotImplementedError


class DirectQueueProvider(QueueProvider):
    """
    Executes or registers jobs directly in-process for local MVP development.
    """
    def send_job(self, queue_name: str, payload: dict):
        # In local mode, jobs are acknowledged immediately
        return {"status": "ENQUEUED_LOCAL", "job": payload}


class SQSQueueProvider(QueueProvider):
    """
    Sends background health check or rollback tasks to Amazon SQS.
    Worker processes (running on EC2 or AWS Lambda) can consume and process messages.
    """
    def __init__(self, queue_url: str, region_name: str = "us-east-1"):
        import boto3
        self.queue_url = queue_url
        self.sqs_client = boto3.client("sqs", region_name=region_name)

    def send_job(self, queue_name: str, payload: dict):
        response = self.sqs_client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(payload),
            MessageAttributes={
                "JobType": {
                    "DataType": "String",
                    "StringValue": queue_name
                }
            }
        )
        return {"status": "ENQUEUED_SQS", "message_id": response.get("MessageId")}


def get_queue_provider() -> QueueProvider:
    """Factory returning active queue provider."""
    if Config.QUEUE_PROVIDER == "sqs" and Config.SQS_QUEUE_URL:
        return SQSQueueProvider(Config.SQS_QUEUE_URL, Config.AWS_REGION)
    return DirectQueueProvider()
