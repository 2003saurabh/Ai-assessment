import boto3
from app.config import settings


def get_aws_session() -> boto3.Session:
    """Create a boto3 session based on the configured auth method."""

    if settings.AWS_AUTH_METHOD == "access_keys":
        # Explicit access keys (CI/CD, non-SSO)
        return boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
        )

    elif settings.AWS_AUTH_METHOD == "sso":
        # SSO profile (local development)
        return boto3.Session(
            profile_name=settings.AWS_PROFILE,
            region_name=settings.AWS_DEFAULT_REGION,
        )

    else:
        # iam_role — no credentials needed, uses instance metadata
        return boto3.Session(
            region_name=settings.AWS_DEFAULT_REGION,
        )
