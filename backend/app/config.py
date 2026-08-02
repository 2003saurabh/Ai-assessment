import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    AWS_AUTH_METHOD: str = os.getenv("AWS_AUTH_METHOD", "sso")  # sso | access_keys | iam_role
    AWS_PROFILE: str = os.getenv("AWS_PROFILE", "default")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")

    # Sonnet for final answers (quality matters)
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    # Haiku for routing + SQL generation (speed matters)
    BEDROCK_FAST_MODEL_ID: str = os.getenv(
        "BEDROCK_FAST_MODEL_ID", "apac.anthropic.claude-3-5-haiku-20241022-v1:0"
    )

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://technova:technova_secret@localhost:5432/technova_db")
    DOCUMENTS_PATH: str = os.getenv("DOCUMENTS_PATH", "data/documents")
    CURRENT_DATE: str = "2026-06-15"


settings = Settings()
