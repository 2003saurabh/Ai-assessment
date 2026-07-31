# TechNova AI Chatbot — Dual-Mode Agentic RAG

A production-grade chatbot that answers questions about TechNova Inc. using two distinct retrieval strategies: **vector-based document search (RAG)** and **text-to-SQL** over structured order data — routed by an LLM agent.

![Architecture](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square)
![Frontend](https://img.shields.io/badge/Frontend-Next.js-000000?style=flat-square)
![LLM](https://img.shields.io/badge/LLM-Claude%20(Bedrock)-7C3AED?style=flat-square)
![Vector Store](https://img.shields.io/badge/Vector%20Store-FAISS-blue?style=flat-square)

## Live Demo

🔗 **[Live URL]** _(deployed at: your-url-here)_

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                       │
│              (Streaming Chat UI + Tool Display)           │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP POST /api/chat (SSE stream)
┌──────────────────────────▼──────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Router Agent (Claude)                 │   │
│  │   Classifies: rag | sql | both | fallback         │   │
│  └────────┬───────────────┬──────────────┬──────────┘   │
│           │               │              │               │
│  ┌────────▼────┐  ┌──────▼──────┐  ┌───▼────────┐     │
│  │  RAG Tool   │  │  SQL Tool   │  │  Fallback  │     │
│  │ FAISS + Emb │  │ SQLite Gen  │  │  Response  │     │
│  └─────────────┘  └─────────────┘  └────────────┘     │
│           │               │                              │
│  ┌────────▼────┐  ┌──────▼──────┐                      │
│  │   FAISS     │  │   SQLite    │                      │
│  │   Index     │  │  (orders)   │                      │
│  └─────────────┘  └─────────────┘                      │
└──────────────────────────────────────────────────────────┘
```

### Request Flow

1. User sends a question via the Next.js frontend.
2. The question hits the `/api/chat` endpoint (FastAPI) with streaming enabled.
3. A **Router Agent** (Claude via Bedrock) classifies the question into one of four categories.
4. Based on the route:
   - **RAG**: Embeds the query → retrieves top-k chunks from FAISS → generates answer with citations.
   - **SQL**: Generates a SQLite query from the question → executes it → summarizes results.
   - **Both**: Runs both pipelines and merges results.
   - **Fallback**: Returns a safe "I don't have that information" response.
5. The response streams back token-by-token to the frontend.

---

## Model & Embedding Choices

| Component | Choice | Reasoning |
|-----------|--------|-----------|
| **LLM** | Claude 3 Sonnet (Bedrock) | Strong reasoning for routing + SQL generation, excellent instruction following, available via AWS Bedrock for production use |
| **Embeddings** | `all-MiniLM-L6-v2` | Fast, lightweight (80MB), good quality for semantic search, runs locally without API costs |
| **Vector Store** | FAISS | In-memory for low latency, no external service needed, easy to Docker-ize, sufficient for small document sets |
| **Database** | SQLite | Zero-config, single-file DB perfect for a small orders table, no external dependencies |

---

## Routing Decision

The agent uses a dedicated LLM call with a classification prompt to route each question. The router considers:

- **Document questions** (policies, product info, how-to) → `rag`
- **Data questions** (revenue, counts, order status) → `sql`
- **Mixed questions** (policy + data cross-reference) → `both`
- **Unrelated questions** → `fallback`

The routing prompt explicitly defines categories and expects a structured JSON response, minimizing ambiguity. This approach was chosen over keyword-matching or embedding-based classification because:
1. It handles nuanced/ambiguous queries better.
2. It can be updated by modifying the prompt without retraining.
3. It generalizes to new question patterns.

---

## Setup & Running

### Prerequisites
- Docker & Docker Compose
- AWS credentials with Bedrock access (Claude model enabled)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/technova-chatbot.git
cd technova-chatbot

# Copy environment file and add your AWS credentials
cp .env.example .env
# Edit .env with your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

# Run with Docker Compose
docker-compose up --build
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Add your credentials
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Configuration & env vars
│   │   ├── models/schemas.py    # Pydantic models
│   │   ├── routers/chat.py      # Chat endpoint with streaming
│   │   └── services/
│   │       ├── agent.py         # Agent routing & orchestration
│   │       ├── llm.py           # Bedrock Claude integration
│   │       ├── vector_store.py  # FAISS index management
│   │       └── database.py      # SQLite query execution
│   ├── data/
│   │   ├── documents/           # Source documents (MD)
│   │   └── orders.csv           # Orders data
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/page.tsx         # Main chat interface
│   │   └── components/          # React components
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Known Limitations

1. **Single-turn routing**: The router classifies each message independently — it doesn't use conversation history for context.
2. **SQL injection surface**: While only SELECT queries are allowed, the LLM-generated SQL is executed directly. A production system would add query sanitization or use parameterized queries.
3. **No conversation memory**: Each question is processed independently. Follow-up questions like "what about last week?" won't resolve context.
4. **Embedding model**: The local embedding model (`all-MiniLM-L6-v2`) is smaller than production-grade options like `text-embedding-3-large`. For larger document sets, a more powerful model would improve retrieval.
5. **Cold start**: First request builds the FAISS index and loads the embedding model, which takes ~10-15 seconds.
6. **Fixed date**: The system treats the current date as June 15, 2026, as specified in the assessment requirements.

---

## Example Questions

| Question | Route | Expected Behavior |
|----------|-------|-------------------|
| "What is the refund window?" | RAG | Answers from returns policy doc |
| "How many orders are pending?" | SQL | Queries orders table |
| "What was total revenue last month?" | SQL | SUM(amount) for May 2026 |
| "What is the maternity leave policy?" | RAG | Answers from HR leave policy |
| "Did order 1031 qualify for a return?" | Both | Checks order date + return policy |
| "What's the weather today?" | Fallback | Safe "I don't have that" response |
