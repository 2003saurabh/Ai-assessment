import json
import logging
from typing import AsyncGenerator

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        from app.services.aws_session import get_aws_session

        session = get_aws_session()
        self.client = session.client("bedrock-runtime")
        self.model_id = settings.BEDROCK_MODEL_ID
        self.fast_model_id = settings.BEDROCK_FAST_MODEL_ID

    def invoke(self, system_prompt: str, user_message: str, use_fast_model: bool = False) -> str:
        """Invoke Bedrock Claude model and return full response.

        Args:
            system_prompt: The system prompt for the model.
            user_message: The user message.
            use_fast_model: If True, uses Haiku (fast) instead of Sonnet (quality).
        """
        model_id = self.fast_model_id if use_fast_model else self.model_id

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            }
        )

        response = self.client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    async def stream(
        self, system_prompt: str, user_message: str
    ) -> AsyncGenerator[str, None]:
        """Stream response from Bedrock Claude model (always uses Sonnet for quality)."""
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            }
        )

        response = self.client.invoke_model_with_response_stream(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk["type"] == "content_block_delta":
                delta = chunk["delta"]
                if delta.get("type") == "text_delta":
                    yield delta["text"]


# Singleton instance
_llm_service = None


def get_llm() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
