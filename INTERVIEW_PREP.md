# Interview Preparation — TechNova Dual-Mode Agentic RAG Chatbot

This document explains every concept, component, and decision in this project from scratch. If you don't know anything about RAG, LLMs, vector databases, or agents — read this top to bottom.

---

## 1. What is This Project?

A chatbot that answers questions about a company called "TechNova" using **two different data sources**:

1. **Documents** (HR policy, product FAQ, return policy) — searched using vector similarity
2. **Database** (orders table with 45 rows) — queried using SQL

The chatbot **automatically decides** which source to use for each question. This is what makes it "agentic" — it has agency to choose tools.

---

## 2. Core Concepts (Know These Cold)

### 2.1 What is RAG?

**RAG = Retrieval Augmented Generation**

Instead of relying on what the LLM was trained on, you:
1. **Retrieve** relevant documents from your own data
2. **Augment** the prompt with those documents
3. **Generate** an answer based on your actual data

**Why RAG?**
- LLMs hallucinate (make stuff up) if they don't know something
- Your company data wasn't in training data
- RAG grounds the LLM's answers in real documents

**Analogy:** It's like an open-book exam. Instead of answering from memory (which might be wrong), you look up the answer in the textbook first.

### 2.2 What is a Vector / Embedding?

An **embedding** is a list of numbers (vector) that represents the **meaning** of text.

```
"What is the return policy?" → [0.23, -0.45, 0.12, ..., 0.89]  (1024 numbers)
"How do I send items back?" → [0.21, -0.43, 0.14, ..., 0.87]  (similar numbers!)
"What's the weather?" → [0.91, 0.33, -0.72, ..., 0.01]  (very different numbers)
```

Texts with similar meanings get similar vectors. This lets us find relevant documents even if the exact words don't match.

### 2.3 What is FAISS?

**FAISS** (Facebook AI Similarity Search) is a library that stores vectors and finds the most similar ones quickly.

Think of it as a special database optimized for "find me the 4 most similar items to this query."

**How it works in this project:**
1. At startup: Split documents into chunks → embed each chunk → store in FAISS
2. At query time: Embed the user's question → find the 4 most similar chunks → use them as context

### 2.4 What is Text-to-SQL?

Instead of searching documents, some questions need **database queries**:
- "How many orders are pending?" → `SELECT COUNT(*) FROM orders WHERE status='pending'`
- "Total revenue last month?" → `SELECT SUM(amount) FROM orders WHERE order_date BETWEEN '2026-05-01' AND '2026-05-31'`

The LLM generates the SQL query from the natural language question. We execute it against SQLite and summarize the results.

### 2.5 What is an "Agent"?

An agent is an LLM that can **decide which tools to use**. Our agent has:
- Tool 1: Vector search (for document questions)
- Tool 2: SQL query (for data questions)
- Tool 3: Both combined
- Tool 4: Fallback (refuse gracefully)

The agent routes each question to the right tool. This routing is itself done by an LLM call.

### 2.6 What is Streaming?

Instead of waiting for the entire answer, we send it **token by token** as the LLM generates it. The user sees text appearing word-by-word (like ChatGPT).

**How:** FastAPI returns a `StreamingResponse`. The frontend reads the response body as a stream using the Fetch API's `reader.read()` loop.

---

## 3. Technology Stack — Why Each Choice

### 3.1 Backend: FastAPI

| Why FastAPI | Explanation |
|-------------|-------------|
| Async native | Streaming requires async — FastAPI handles this naturally |
| Fast | Built on Starlette, one of the fastest Python frameworks |
| Auto-docs | Swagger UI at `/docs` for free |
| Type-safe | Pydantic models validate request/response |

**Interview Q: "Why not Flask?"**
> Flask doesn't have native async support. Streaming responses in Flask require workarounds. FastAPI was purpose-built for async operations and has better streaming support.

### 3.2 LLM: Claude 3.5 Sonnet via AWS Bedrock

| Why | Explanation |
|-----|-------------|
| Claude 3.5 Sonnet | Strong at reasoning, SQL generation, and following complex instructions |
| AWS Bedrock | Managed service, no GPU management, pay-per-token, enterprise-grade |
| Inference Profile | Required in ap-south-1 region for on-demand access |

**Interview Q: "Why Bedrock instead of direct Anthropic API?"**
> Bedrock gives us enterprise features: VPC endpoints, CloudWatch logging, IAM-based auth, no API key management, and seamless integration with other AWS services. In production, this matters.

**Interview Q: "Why Claude over GPT-4?"**
> Claude excels at instruction-following and structured output (JSON routing). It's also very good at generating correct SQL. Either would work — this is a defensible choice, not the only right one.

### 3.3 Embeddings: Amazon Titan Embed Text v2

| Why | Explanation |
|-----|-------------|
| No local model | Eliminates PyTorch (~2GB) from the Docker image |
| Fast API call | ~100ms per embedding vs loading a model into memory |
| Good quality | 1024-dimensional embeddings, trained for semantic search |
| Same auth | Uses the same Bedrock credentials as Claude |

**Interview Q: "Why not a local embedding model like sentence-transformers?"**
> Local models require PyTorch (2GB+), making the Docker image huge and startup slow. Titan is a single API call per embedding. For a small document set (3 files), the latency is negligible and the image stays under 500MB.

### 3.4 Vector Store: FAISS

| Why | Explanation |
|-----|-------------|
| Zero infrastructure | No external service to manage (unlike Pinecone/pgvector) |
| Fast | In-memory search, microsecond lookups |
| Simple | Single file on disk, easy to Docker-ize |
| Sufficient | For 3 documents (~50 chunks), we don't need a distributed vector DB |

**Interview Q: "When would you NOT use FAISS?"**
> When you have millions of documents, need real-time updates without rebuilding, need filtering/metadata queries, or need horizontal scaling. Then use Pinecone, pgvector, or Qdrant.

### 3.5 Database: SQLite

| Why | Explanation |
|-----|-------------|
| Zero config | Single file, no server process |
| Built into Python | `import sqlite3` — nothing to install |
| Perfect for 45 rows | No need for PostgreSQL overhead |

### 3.6 Frontend: Next.js

| Why | Explanation |
|-----|-------------|
| Required | Assessment mandates Next.js |
| SSR capable | Though we use client-side rendering for the chat |
| Tailwind | Rapid UI development with utility classes |
| Standalone output | Docker-friendly production build |

---

## 4. How the Routing Works (Critical for Interview)

This is the most important architectural decision. When a user asks a question:

```
User: "What was total revenue last month?"
         │
         ▼
┌─────────────────────────┐
│   ROUTING LLM CALL      │ ← Claude classifies the question
│                         │
│   Input: question       │
│   Output: JSON          │
│   {"route": "sql"}      │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   SQL GENERATION        │ ← Claude writes the SQL
│                         │
│   SELECT SUM(amount)    │
│   FROM orders           │
│   WHERE order_date      │
│   BETWEEN '2026-05-01'  │
│   AND '2026-05-31'      │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   EXECUTE QUERY         │ ← SQLite runs it
│                         │
│   Result: [{"total":    │
│   5765.00}]             │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   ANSWER GENERATION     │ ← Claude summarizes (STREAMED)
│                         │
│   "The total revenue    │
│   for May 2026 was      │
│   $5,765.00"            │
└─────────────────────────┘
```

### The Router Prompt

```
Classify into:
- "rag" → policy/product questions (answered from documents)
- "sql" → data questions (revenue, counts, order status)
- "both" → mixed (need documents + database)
- "fallback" → unrelated questions

Respond with ONLY JSON: {"route": "...", "reasoning": "..."}
```

**Interview Q: "Why use an LLM for routing instead of keyword matching?"**
> Keyword matching breaks on nuanced queries. "Did order 1031 qualify for a return?" has the word "order" (SQL?) and "return" (RAG?). The LLM understands this needs BOTH. A regex can't handle this ambiguity.

**Interview Q: "Why not use embeddings for routing?"**
> You could embed example questions for each category and find the nearest match. But this requires maintaining training examples and doesn't handle novel phrasings well. The LLM approach generalizes better and is easier to update (just modify the prompt).

---

## 5. The Streaming Protocol (Important Technical Detail)

The response stream has two parts:

**Part 1: Metadata (first line)**
```json
{"type": "metadata", "tool_used": "sql", "sql_query": "SELECT...", "citations": null}
```

**Part 2: Answer tokens (everything after first newline)**
```
The total revenue for May 2026 was $5,765.00 based on...
```

The frontend splits on the first `\n`:
- Before `\n` → parse as JSON → extract tool_used, sql_query, citations
- After `\n` → append to message content (renders as text appears)

**Interview Q: "Why not use Server-Sent Events (SSE)?"**
> SSE would also work and is more structured. We chose plain streaming for simplicity — no event framing overhead, and the metadata-then-tokens protocol is simple enough. In production, SSE or WebSockets would be better for reconnection handling.

---

## 6. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| SQL Injection | Only SELECT queries allowed (checked before execution) |
| Hallucination | RAG grounds answers in documents; fallback for unknowns |
| Prompt Injection | Router prompt is in system message (harder to override) |
| AWS Credentials | SSO tokens expire; IAM roles in production; no hardcoded keys |
| Data Access | SQLite is read-only after setup; no write operations exposed |

**Interview Q: "How would you prevent SQL injection?"**
> Currently we check if the query starts with SELECT. In production, I'd add: (1) parameterized queries where possible, (2) a query allowlist/deny of dangerous keywords (DROP, DELETE, INSERT), (3) run SQL in a read-only connection, (4) limit query execution time.

---

## 7. Known Limitations (Be Honest About These)

| Limitation | Why | How to Fix |
|-----------|-----|------------|
| No conversation memory | Each question is independent | Add message history to Claude calls |
| Cold start (~5s) | FAISS index builds on first request | Pre-build during Docker image creation or use a startup script |
| Single-turn routing | Can't do "what about last week?" | Track context across turns |
| No query validation | LLM might generate bad SQL | Add retry logic + SQL validation |
| Fixed date | Hardcoded to June 15, 2026 | Use `datetime.now()` in production |
| No auth on API | Anyone can call the endpoint | Add API key or JWT auth |

**Interview Q: "What would you add if you had more time?"**
> 1. Conversation memory (track chat history per session)
> 2. Retry with feedback (if SQL fails, tell Claude the error and ask for a fix)
> 3. Confidence-based routing (if the router is uncertain, ask the user to clarify)
> 4. Caching (same question → same answer, save LLM costs)
> 5. Observability (log every routing decision, latency, token usage)

---

## 8. Cost Analysis

| Operation | Model | Cost (approx) |
|-----------|-------|----------------|
| Routing call | Claude 3.5 Sonnet | ~$0.003 per question |
| SQL generation | Claude 3.5 Sonnet | ~$0.003 per question |
| Answer generation | Claude 3.5 Sonnet | ~$0.01 per answer (longer output) |
| Embedding (query) | Titan Embed v2 | ~$0.0001 per query |
| Embedding (index build) | Titan Embed v2 | ~$0.005 total (one-time, ~50 chunks) |

**Total cost per question: ~$0.015 (1.5 cents)**

For 1000 questions/day = ~$15/day = ~$450/month

**Interview Q: "How would you reduce costs?"**
> 1. Use Claude Haiku for routing (cheaper, still accurate for classification)
> 2. Cache frequent questions
> 3. Use a smaller/cheaper model for SQL generation
> 4. Batch embeddings

---

## 9. How Each File Works (Quick Reference)

### Backend

| File | What it does | Key functions |
|------|-------------|---------------|
| `main.py` | Creates FastAPI app, adds CORS, mounts routers | `app` instance |
| `config.py` | Reads all env vars into a Settings class | `settings` singleton |
| `chat.py` | HTTP endpoint, creates StreamingResponse | `chat()`, `health()` |
| `aws_session.py` | Creates boto3 session based on auth method | `get_aws_session()` |
| `agent.py` | Routes questions, orchestrates tools, streams answers | `process_question()`, `_route_question()`, `_generate_sql()`, `_get_rag_context()` |
| `llm.py` | Calls Bedrock Claude (sync + streaming) | `invoke()`, `stream()` |
| `vector_store.py` | Manages FAISS index + Bedrock Titan embeddings | `search()`, `_build_index()`, `embed_query()` |
| `database.py` | SQLite setup + query execution | `execute_query()`, `get_schema()` |

### Frontend

| File | What it does |
|------|-------------|
| `page.tsx` | Main chat UI, manages messages state, handles streaming fetch |
| `ChatMessage.tsx` | Renders message bubbles, tool badges, SQL display, citations |
| `ChatInput.tsx` | Text input, send button, loading state |
| `layout.tsx` | Root HTML layout with metadata |
| `globals.css` | Tailwind imports + dark theme |

---

## 10. Potential Interview Questions & Answers

### Architecture

**Q: "Walk me through the architecture."**
> User sends a message from the Next.js frontend to the FastAPI backend via POST /api/chat. The backend has an Agent that first calls Claude to classify the question into one of four routes: RAG, SQL, both, or fallback. Based on the route, it either searches the FAISS vector index for relevant document chunks, generates and executes SQL against SQLite, or does both. The final answer is generated by Claude using the retrieved context, and streamed back token-by-token to the frontend which displays it in real-time.

**Q: "Why a single agent instead of separate endpoints for RAG and SQL?"**
> The assessment requires the chatbot to decide on its own which source to use. A single agent with routing gives us: (1) unified UX — user doesn't need to know which tool to ask, (2) ability to combine both for mixed questions, (3) graceful fallback for out-of-scope questions.

### RAG Specifics

**Q: "How do you chunk the documents?"**
> I use RecursiveCharacterTextSplitter with 500-char chunks and 50-char overlap. The separators prioritize splitting at headers (##, ###), then paragraphs, then sentences. This keeps semantic units together while staying within embedding model limits.

**Q: "Why 500 characters?"**
> It's a balance. Too small (100) → loses context. Too large (2000) → dilutes relevance when searching. 500 gives enough context per chunk while keeping search precise. The 50-char overlap ensures we don't lose information at chunk boundaries.

**Q: "How do you handle citations?"**
> Each chunk in FAISS stores metadata including the source filename. When we retrieve chunks, we extract unique source filenames and pass them as citations. The LLM is instructed to reference sources in its answer.

### SQL Specifics

**Q: "How do you prevent the LLM from generating harmful SQL?"**
> Three layers: (1) The prompt only asks for SELECT queries. (2) Before execution, we check the query starts with SELECT — reject anything else. (3) SQLite connection is to a file with limited data. In production, I'd add a read-only connection and query timeout.

**Q: "What if the generated SQL is wrong?"**
> Currently, if execution fails, we return the error to the user. A better approach would be: catch the error, send it back to Claude with "this SQL failed with error X, please fix it", and retry once. This is a common pattern called "self-healing SQL generation."

### Production Readiness

**Q: "How would you scale this?"**
> 1. Put the backend behind a load balancer (ALB)
> 2. Run multiple container replicas (ECS/EKS)
> 3. Move FAISS to a shared volume or switch to a managed vector DB
> 4. Move SQLite to RDS/Aurora for concurrent access
> 5. Add Redis for caching frequent queries
> 6. Add API Gateway for rate limiting and auth

**Q: "How would you monitor this in production?"**
> 1. CloudWatch for Bedrock API latency and errors
> 2. Custom metrics: routing decisions, token usage per request, query execution time
> 3. Log every routing decision for analysis (was it correct?)
> 4. Alert on error rate spikes or latency > 10s
> 5. Track cost per request

**Q: "How would you test this?"**
> 1. Unit tests: test routing with known questions, test SQL generation
> 2. Integration tests: end-to-end question → answer with mocked Bedrock
> 3. Evaluation set: 50+ questions with expected answers, run weekly
> 4. A/B testing routing strategies

---

## 11. Glossary

| Term | Meaning |
|------|---------|
| **RAG** | Retrieval Augmented Generation — find relevant docs, then generate answer |
| **Embedding** | A vector (list of numbers) representing the meaning of text |
| **FAISS** | Facebook AI Similarity Search — fast nearest-neighbor vector search |
| **Vector Store** | Database optimized for storing and searching embeddings |
| **Chunking** | Splitting documents into smaller pieces for embedding |
| **Token** | A piece of text (~4 chars in English). LLMs process tokens, not words |
| **Streaming** | Sending response piece-by-piece instead of all at once |
| **Inference Profile** | AWS Bedrock concept — a resource identifier for cross-region model access |
| **Agent** | An LLM that decides which tools to use based on the question |
| **Text-to-SQL** | Converting natural language to SQL queries using an LLM |
| **System Prompt** | Instructions given to the LLM that shape its behavior |
| **Hallucination** | When an LLM generates confident but incorrect information |
| **Cold Start** | First-time initialization delay (building index, loading models) |
| **SSO** | Single Sign-On — AWS identity federation for human users |
| **IAM Role** | AWS identity for services (no passwords, auto-rotating credentials) |
| **Bedrock** | AWS managed service for accessing foundation models (Claude, Titan, etc.) |

---

## 12. What to Demo

When showing the project, demonstrate these scenarios in order:

1. **RAG working:** "What is the refund window?" → Shows Document Search badge + citation
2. **SQL working:** "How many orders are pending?" → Shows Database Query badge + SQL
3. **Both working:** "Did order 1031 qualify for a return?" → Shows Both badge + SQL + citation
4. **Fallback working:** "What's the weather?" → Shows Out of Scope badge
5. **Streaming:** Watch tokens appear one-by-one (real-time feel)
6. **Architecture:** Pull up the README diagram
7. **Code:** Show the agent.py routing logic

---

## 13. One-Liner Answers for Quick Questions

- **"What's the tech stack?"** → FastAPI + Next.js + AWS Bedrock (Claude) + FAISS + SQLite
- **"How does routing work?"** → LLM classifies each question into rag/sql/both/fallback
- **"Why FAISS?"** → Zero infrastructure, fast, sufficient for small doc sets
- **"Why Bedrock?"** → Managed, no GPU, IAM auth, enterprise-grade
- **"How do you stream?"** → Bedrock's `invoke_model_with_response_stream` → FastAPI `StreamingResponse` → Frontend `fetch` with `reader.read()` loop
- **"How do you prevent hallucination?"** → RAG grounds answers in real docs; fallback for unknowns; LLM instructed to only use provided context
- **"What's the cost?"** → ~1.5 cents per question
- **"How would you scale?"** → Multiple replicas behind ALB, managed vector DB, RDS for SQL, Redis cache


---

## 14. Missing Topics — Deep Dives

### 14.1 Singleton Pattern (Used Everywhere)

Every service uses a singleton pattern:

```python
_agent_service = None

def get_agent() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
```

**Why?**
- FAISS index loads once (not per request)
- SQLite connection setup happens once
- Bedrock client is reused (connection pooling)
- First request is slow (cold start), subsequent requests are fast

**Interview Q: "Isn't global state bad?"**
> In a web server, you want expensive resources (DB connections, model weights, indexes) to persist across requests. FastAPI runs in a single process, so globals are safe. In multi-worker setups, each worker gets its own singleton — which is fine since FAISS is read-only.

---

### 14.2 Error Handling & JSON Parsing

The routing function has defensive parsing:

```python
def _route_question(self, question: str) -> dict:
    response = self.llm.invoke(ROUTER_SYSTEM_PROMPT, question)
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        # Fallback: try to extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
        return {"route": "fallback", "reasoning": "Could not parse"}
```

**Why this matters:**
- LLMs sometimes add text before/after JSON ("Sure! Here's the classification: {...}")
- We try strict parsing first, then extract JSON, then fallback safely
- The system never crashes — worst case is a fallback response

**Interview Q: "What if the LLM returns invalid JSON?"**
> We have three levels of fallback: (1) try direct parse, (2) try extracting JSON substring, (3) default to fallback route. The user always gets a response, even if routing fails.

---

### 14.3 SQL Sanitization

```python
sql_clean = sql_query.replace("```sql", "").replace("```", "").strip()
```

**Why?** Claude sometimes wraps SQL in markdown code blocks. We strip those before executing.

Additionally in `database.py`:
```python
sql_stripped = sql.strip().upper()
if not sql_stripped.startswith("SELECT"):
    return {"error": "Only SELECT queries are allowed.", "results": []}
```

**Interview Q: "Is this enough for production?"**
> No. For production I'd add: (1) a SQL parser to validate the AST, (2) blocklist keywords like DROP/DELETE/ALTER/INSERT, (3) execute with a read-only database connection, (4) query timeout (e.g., 5 seconds max), (5) limit result rows returned.

---

### 14.4 The Bedrock API (Know How It Works)

**Request format (Anthropic Messages API on Bedrock):**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 2048,
  "system": "You are a routing agent...",
  "messages": [
    {"role": "user", "content": "What is the refund window?"}
  ]
}
```

**Non-streaming response:**
```json
{
  "content": [{"type": "text", "text": "The refund window is 30 days..."}],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 150, "output_tokens": 45}
}
```

**Streaming response events:**
```json
{"type": "content_block_start", "content_block": {"type": "text", "text": ""}}
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "The"}}
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": " refund"}}
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": " window"}}
{"type": "message_stop"}
```

We only yield `text_delta` content — ignoring start/stop events.

**Interview Q: "What's the difference between `invoke_model` and `invoke_model_with_response_stream`?"**
> `invoke_model` waits for the full response (blocking). `invoke_model_with_response_stream` returns an event stream immediately — we iterate over events and yield tokens as they arrive. We use blocking for routing/SQL generation (need the full answer before proceeding) and streaming for the final answer (user sees it live).

---

### 14.5 CORS (Cross-Origin Resource Sharing)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allows any frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Why needed?** Frontend (localhost:3000) and backend (localhost:8000) are different origins. Browsers block cross-origin requests by default. CORS headers tell the browser it's okay.

**Interview Q: "Would you keep `allow_origins=["*"]` in production?"**
> No. In production I'd restrict to the specific frontend domain: `allow_origins=["https://app.technova.com"]`. Wildcard is fine for development but a security risk in production.

---

### 14.6 Docker Multi-Stage Build (Frontend)

```dockerfile
# Stage 1: Install dependencies
FROM node:20-alpine AS deps
COPY package.json ./
RUN npm install

# Stage 2: Build the app
FROM node:20-alpine AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Production image (minimal)
FROM node:20-alpine AS runner
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
CMD ["node", "server.js"]
```

**Why multi-stage?**
- Build tools and `node_modules` (200MB+) don't end up in the final image
- Production image is just Node.js + the compiled app (~50MB)
- Faster deploys, less attack surface

**Interview Q: "What's `standalone` output in Next.js?"**
> `output: "standalone"` in `next.config.js` makes Next.js produce a self-contained server that doesn't need `node_modules`. It bundles only the required dependencies. This is essential for Docker — keeps the image small.

---

### 14.7 Frontend State Management

The chat uses React's `useState` — no Redux, no Zustand:

```typescript
const [messages, setMessages] = useState<Message[]>([]);
const [isLoading, setIsLoading] = useState(false);
```

**Why no state library?**
> The state is simple: a list of messages and a loading flag. No shared state between components, no complex updates. useState is the right tool. Adding Redux for this would be over-engineering.

**The streaming update pattern:**
```typescript
setMessages((prev) => {
  const updated = [...prev];
  updated[updated.length - 1] = { ...msg, content: fullContent, toolInfo };
  return updated;
});
```

This replaces the last message on every chunk — creating the "typing" effect.

---

### 14.8 Similarity Score & Top-K

```python
results = self.vector_store.similarity_search_with_score(query, k=4)
```

- **k=4**: We retrieve the top 4 most relevant chunks.
- **Score**: FAISS returns L2 distance (lower = more similar). We include it in results for debugging.

**Interview Q: "Why top-4? Why not top-1 or top-10?"**
> Top-1 risks missing relevant info spread across chunks. Top-10 fills the context window with noise. Top-4 is a sweet spot — enough context without diluting relevance. We could make this configurable or use a score threshold instead.

**Interview Q: "What if all 4 chunks are from the same document?"**
> That's fine — it means the answer is concentrated in one source. We still deduplicate citations (show each source file only once). If we wanted diversity, we could add MMR (Maximal Marginal Relevance) which penalizes chunks similar to already-selected ones.

---

### 14.9 The `process_question` Flow (Complete)

```python
async def process_question(self, question: str) -> AsyncGenerator[str, None]:
```

This is an **async generator** — it uses `yield` to send data as it becomes available:

1. `yield json.dumps(metadata) + "\n"` → sends tool info to frontend
2. `async for token in self.llm.stream(...)` → yields each token from Claude
3. Frontend reads these yields as stream chunks

**Interview Q: "Why is it an async generator and not a regular function?"**
> A regular function would need to collect all tokens into a string and return at the end — no streaming. An async generator yields each token as it arrives from Bedrock, so the frontend gets them immediately. This is what enables the real-time typing effect.

---

### 14.10 The "Both" Route (Cross-Referencing)

For questions like "Did order 1031 qualify for a return?":

1. **RAG retrieval** → finds the return policy (30-day window from delivery)
2. **SQL generation** → `SELECT * FROM orders WHERE order_id = 1031` → gets order_date
3. **Combined prompt** → Claude sees both the policy AND the order data
4. **Claude reasons** → "Order 1031 was June 1. Current date is June 15. That's 14 days. Within 30-day window. Yes, eligible."

This is the most impressive capability to demo — it shows true "agentic" behavior combining multiple sources.

---

### 14.11 LangChain Usage (Minimal)

We use LangChain for:
- `FAISS` wrapper (load/save/search)
- `RecursiveCharacterTextSplitter` (chunking)
- `DirectoryLoader` + `TextLoader` (loading files)
- `Embeddings` base class (custom implementation)

We do NOT use LangChain for:
- LLM calls (direct boto3)
- Agent framework (custom routing)
- Chains or memory

**Interview Q: "Why not use LangChain's agent framework?"**
> LangChain's agent framework adds abstraction layers that make debugging harder and add latency. For a simple two-tool routing system, our custom 100-line agent is clearer, faster, and easier to explain. We only use LangChain where it genuinely saves effort (FAISS integration, text splitting).

---

### 14.12 Prompt Engineering Decisions

| Prompt | Key Design Choices |
|--------|-------------------|
| Router | "Respond with ONLY JSON" — prevents extra text. Categories defined explicitly with examples. |
| SQL Gen | Includes full schema + date context. "Only generate SELECT" — guardrail. |
| RAG Answer | "Based ONLY on the provided context" — prevents hallucination. "Include citations" — traceability. |
| SQL Answer | "Format numbers nicely" — UX improvement. "Do NOT make up data" — accuracy. |
| Both Answer | "Cite document sources" + "Reference specific data" — structured combining. |

**Interview Q: "How would you improve the prompts?"**
> 1. Add few-shot examples (show the model what good routing looks like)
> 2. Add chain-of-thought for SQL generation (think step-by-step before writing SQL)
> 3. Add output format constraints for the answer (bullet points, max length)
> 4. Temperature control (0 for routing/SQL, 0.3 for answers)

---

## 15. Comparison with Alternatives

### "Why not use LangChain's full agent framework?"

| Our Approach | LangChain Agents |
|-------------|-----------------|
| ~100 lines of routing code | 500+ lines of framework code |
| Easy to debug (print each step) | Black-box, hard to trace decisions |
| Exact control over prompts | Prompt templates often hidden |
| Fast (3 LLM calls max) | Can loop multiple times (unpredictable) |
| Predictable cost | Cost varies per question |

### "Why not use OpenAI function calling?"

| Our Approach | Function Calling |
|-------------|-----------------|
| Works with any LLM (Claude, GPT, etc.) | Tied to OpenAI or compatible APIs |
| Separate routing step = transparent | Implicit tool selection in one call |
| Can explain routing reasoning | Decision is opaque |
| More LLM calls (slower) | Fewer calls (faster) |

### "Why not embed everything including orders data?"

The assessment explicitly says: "structured data is not embedded for vector search; the agent writes a query against it."

But even without that constraint — embedding tabular data loses the ability to do aggregations (SUM, COUNT, AVG), filtering, and joins. SQL is the right tool for structured queries.

---

## 16. AWS-Specific Knowledge

### What is an Inference Profile?

In some AWS regions, you can't call models directly. You need an "inference profile" — a resource that provides on-demand access to a model.

```
Direct model ID: anthropic.claude-3-5-sonnet-20241022-v2:0  ← FAILS in ap-south-1
Inference profile: apac.anthropic.claude-3-5-sonnet-20241022-v2:0  ← WORKS
```

**Interview Q: "Why does the model ID have 'apac' prefix?"**
> AWS Bedrock uses cross-region inference profiles. `apac.*` means the request is routed to the nearest APAC region that has the model available. This is how newer models are exposed in regions where they're not natively deployed.

### IAM Permissions Needed

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "*"
}
```

Minimum permissions. In production, scope the Resource to specific model ARNs.

### SSO vs IAM Roles

| SSO (Development) | IAM Roles (Production) |
|-------------------|----------------------|
| Human users | Services/containers |
| Tokens expire (need re-login) | Auto-rotated by AWS |
| Requires browser auth flow | No human interaction |
| Stored in ~/.aws/sso/cache | Fetched from IMDS |

---

## 17. Edge Cases You Should Know

| Edge Case | What Happens |
|-----------|-------------|
| Empty message | Frontend prevents sending (disabled button) |
| Very long question | Works — Bedrock has 200K token context window |
| SQL returns 0 rows | Claude says "no results found" |
| SQL execution error | Error shown to user with the SQL that failed |
| FAISS index doesn't exist | Built automatically on first request |
| Bedrock rate limit hit | 500 error → frontend shows generic error |
| SSO token expired | 403 from Bedrock → need to re-login |
| Network disconnection mid-stream | Frontend shows partial answer + error state |
| Special characters in question | Handled — JSON encoding takes care of it |
| Concurrent requests | Each request gets its own streaming response; singletons are thread-safe for reads |

---

## 18. Performance Characteristics

| Operation | Latency |
|-----------|---------|
| Routing (Claude call) | 1-2 seconds |
| Embedding (Titan call) | 100-200ms |
| FAISS search (in-memory) | <1ms |
| SQL generation (Claude call) | 1-2 seconds |
| SQLite execution | <1ms |
| Answer streaming (first token) | 1-2 seconds |
| Total time to first token | 2-4 seconds (RAG) / 3-5 seconds (SQL) |

**Bottleneck:** LLM calls dominate. Everything else is negligible.

**Interview Q: "How would you reduce latency?"**
> 1. Parallelize where possible (RAG retrieval + SQL generation can run concurrently for "both" route)
> 2. Use Claude Haiku for routing (faster, cheaper)
> 3. Cache routing decisions for repeated questions
> 4. Pre-warm the singleton on app startup (not on first request)

---

## 19. Final Checklist Before Interview

- [ ] Can explain RAG in one sentence
- [ ] Can explain why FAISS over Pinecone/pgvector
- [ ] Can explain the routing flow (3 LLM calls)
- [ ] Can explain why Claude via Bedrock
- [ ] Can explain the streaming protocol (metadata + tokens)
- [ ] Can explain text-to-SQL with safety measures
- [ ] Can articulate 3 limitations and how to fix them
- [ ] Can describe how to scale to production
- [ ] Can demo all 4 routes (RAG, SQL, both, fallback)
- [ ] Know the cost per question (~1.5 cents)
- [ ] Can explain Docker multi-stage build
- [ ] Can explain SSO vs access keys vs IAM roles
- [ ] Can answer "what would you do differently?"
