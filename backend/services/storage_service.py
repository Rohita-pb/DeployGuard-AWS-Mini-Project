import os
from pathlib import Path
from backend.config import Config


class StorageProvider:
    """Base interface for storing reports and deployment artifacts."""
    def save_file(self, filename: str, content: str) -> str:
        raise NotImplementedError

    def get_file(self, filename: str) -> str:
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    """Stores reports locally in the backend/reports folder."""
    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent / "reports"
        else:
            self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, filename: str, content: str) -> str:
        file_path = self.base_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(file_path)

    def get_file(self, filename: str) -> str:
        file_path = self.base_dir / filename
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


class S3StorageProvider(StorageProvider):
    """
    Stores reports in Amazon S3 for cloud deployment.
    Uses boto3 with IAM role or environment credentials.
    """
    def __init__(self, bucket_name: str, region_name: str = "us-east-1"):
        import boto3
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3", region_name=region_name)

    def save_file(self, filename: str, content: str) -> str:
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f"reports/{filename}",
            Body=content.encode("utf-8"),
            ContentType="text/csv"
        )
        return f"s3://{self.bucket_name}/reports/{filename}"

    def get_file(self, filename: str) -> str:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=f"reports/{filename}")
        return response["Body"].read().decode("utf-8")


def get_storage_provider() -> StorageProvider:
    """Factory function returning the configured storage provider."""
    if Config.STORAGE_PROVIDER == "s3" and Config.S3_BUCKET_NAME:
        return S3StorageProvider(Config.S3_BUCKET_NAME, Config.AWS_REGION)
    return LocalStorageProvider()
