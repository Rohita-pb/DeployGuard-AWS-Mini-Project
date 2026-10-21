import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from workspace root if present
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "deployguard-mvp-secret-key-2026")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", 5000))

    # Database Configuration:
    # Defaults to local SQLite file in backend directory if not provided.
    # Future Amazon RDS MySQL connection format:
    # mysql+pymysql://<user>:<password>@<rds-endpoint>:3306/<database_name>
    DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent / "deployguard.db"
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
    )

    # Health Check & SSRF Protection Settings
    # In production, ALLOW_LOCAL_HEALTHCHECKS must remain False to prevent SSRF
    ALLOW_LOCAL_HEALTHCHECKS = os.environ.get("ALLOW_LOCAL_HEALTHCHECKS", "false").lower() in ("true", "1", "yes")
    HEALTH_CHECK_TIMEOUT_SECONDS = int(os.environ.get("HEALTH_CHECK_TIMEOUT_SECONDS", 5))
    MAX_RESPONSE_SIZE_BYTES = int(os.environ.get("MAX_RESPONSE_SIZE_BYTES", 1024 * 1024))  # 1MB limit

    # Future AWS Modular Integrations
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "local")  # 'local' or 's3'
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
    NOTIFICATION_PROVIDER = os.environ.get("NOTIFICATION_PROVIDER", "local")  # 'local' or 'sns'
    SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
    QUEUE_PROVIDER = os.environ.get("QUEUE_PROVIDER", "direct")  # 'direct' or 'sqs'
    SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")


class TestConfig(Config):
    """Configuration used for automated unit tests."""
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    ALLOW_LOCAL_HEALTHCHECKS = True
