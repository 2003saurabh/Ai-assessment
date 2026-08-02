from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest
from app.services.agent import get_agent
from app.services.database import get_database

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
    db = get_database()
    db_healthy = db.is_healthy()

    status = "healthy" if db_healthy else "degraded"
    return {
        "status": status,
        "components": {
            "database": "up" if db_healthy else "down",
        },
    }
