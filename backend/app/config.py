import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    AWS_AUTH_METHOD: str = os.getenv("AWS_AUTH_METHOD", "sso")  # sso | access_keys | iam_role
    AWS_PROFILE: str = os.getenv("AWS_PROFILE", "default")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "data/faiss_index")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/orders.db")
    DOCUMENTS_PATH: str = os.getenv("DOCUMENTS_PATH", "data/documents")
    CURRENT_DATE: str = "2026-06-15"


settings = Settings()
