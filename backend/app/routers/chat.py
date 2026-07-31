from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest
from app.services.agent import get_agent

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with token-level streaming."""
    agent = get_agent()

    async def generate():
        async for token in agent.process_question(request.message):
            yield token

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def health():
    return {"status": "healthy"}
