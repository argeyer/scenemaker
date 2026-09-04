"""S3-compatible storage (AWS S3, Cloudflare R2, MinIO)."""

import boto3


class S3Storage:
    def __init__(self, bucket: str, *, region: str, endpoint_url: str | None = None) -> None:
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except self.client.exceptions.ClientError:
            return False
        return True

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def download_url(self, key: str, ttl_seconds: int) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=ttl_seconds
        )
