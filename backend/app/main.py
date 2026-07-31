from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat

app = FastAPI(
    title="TechNova AI Chatbot",
    description="Dual-Mode Agentic RAG Chatbot with Vector Search and Text-to-SQL",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    return {
        "message": "TechNova AI Chatbot API",
        "docs": "/docs",
        "health": "/api/health",
    }
