# Runbook — TechNova Dual-Mode Agentic RAG Chatbot

This document provides a detailed breakdown of every component in this project. It is intended for anyone who needs to understand, maintain, debug, or extend the system.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Directory Structure](#directory-structure)
4. [Backend Deep Dive](#backend-deep-dive)
   - [Entry Point & API Layer](#entry-point--api-layer)
   - [Configuration](#configuration)
   - [AWS Session Management](#aws-session-management)
   - [Agent Service (Router)](#agent-service-router)
   - [LLM Service](#llm-service)
   - [Vector Store Service](#vector-store-service)
   - [Database Service](#database-service)
5. [Frontend Deep Dive](#frontend-deep-dive)
   - [Page & Layout](#page--layout)
   - [Components](#components)
   - [Streaming Protocol](#streaming-protocol)
6. [Data Layer](#data-layer)
   - [Documents (Unstructured)](#documents-unstructured)
   - [Orders Table (Structured)](#orders-table-structured)
7. [Authentication & AWS Setup](#authentication--aws-setup)
8. [Docker & Deployment](#docker--deployment)
9. [Request Lifecycle (End-to-End)](#request-lifecycle-end-to-end)
10. [Troubleshooting](#troubleshooting)
11. [Extending the System](#extending-the-system)

---

## Project Overview

This is a single chatbot that answers questions about a fictional company (TechNova Inc.) using two retrieval strategies:

| Mode | Source | Use Case |
|------|--------|----------|
| **Agentic RAG** | FAISS vector index over Markdown documents | Policy questions, product info |
| **Text-to-SQL** | SQLite database with orders table | Revenue, order counts, status queries |
| **Both** | Combines RAG + SQL | Cross-referencing policy with order data |
| **Fallback** | None | Out-of-scope questions get a safe response |

An LLM-powered routing agent decides per-question which tool to invoke.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     User (Browser)                            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    HTTP POST /api/chat
                    (streams response back)
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                   FRONTEND (Next.js 15)                        │
│                   Port: 3000                                  │
│                                                               │
│  • Sends user message to backend                              │
│  • Reads streaming response chunk by chunk                    │
│  • First chunk = JSON metadata (tool_used, citations, sql)    │
│  • Remaining chunks = answer tokens                           │
│  • Renders tool badges, citations, expandable SQL             │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    HTTP POST (fetch with streaming)
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                   BACKEND (FastAPI)                            │
│                   Port: 8000                                  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  AGENT SERVICE                          │  │
│  │                                                        │  │
│  │  1. Receives question                                  │  │
│  │  2. Calls Claude to ROUTE (rag/sql/both/fallback)      │  │
│  │  3. Executes the chosen tool(s)                        │  │
│  │  4. Streams final answer via Claude                    │  │
│  └────────┬──────────────────┬───────────────┬───────────┘  │
│           │                  │               │               │
│  ┌────────▼──────┐  ┌───────▼───────┐  ┌───▼───────────┐  │
│  │  VECTOR STORE │  │   DATABASE    │  │   FALLBACK    │  │
│  │               │  │               │  │               │  │
│  │ • Embeds query│  │ • Generates   │  │ • Returns     │  │
│  │   via Titan   │  │   SQL via     │  │   static      │  │
│  │ • Searches    │  │   Claude      │  │   message     │  │
│  │   FAISS index │  │ • Executes    │  │               │  │
│  │ • Returns top │  │   against     │  │               │  │
│  │   4 chunks +  │  │   SQLite      │  │               │  │
│  │   citations   │  │ • Returns     │  │               │  │
│  │               │  │   results     │  │               │  │
│  └───────────────┘  └───────────────┘  └───────────────┘  │
│           │                  │                               │
│  ┌────────▼──────┐  ┌───────▼───────┐                      │
│  │  FAISS Index  │  │  SQLite DB    │                      │
│  │  (on disk)    │  │  (orders.db)  │                      │
│  └───────────────┘  └───────────────┘                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              AWS BEDROCK (External)                     │  │
│  │                                                        │  │
│  │  • Claude 3.5 Sonnet v2 — routing, SQL gen, answers    │  │
│  │  • Titan Embed Text v2 — document embeddings           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
AI-chatbot/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, CORS, router registration
│   │   ├── config.py              # All configuration (env vars, defaults)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py         # Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── chat.py            # /api/chat and /api/health endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── aws_session.py     # AWS session factory (SSO/keys/IAM role)
│   │       ├── agent.py           # Core routing logic + orchestration
│   │       ├── llm.py             # Bedrock Claude invocation + streaming
│   │       ├── vector_store.py    # FAISS index + Bedrock Titan embeddings
│   │       └── database.py        # SQLite setup + query execution
│   ├── data/
│   │   ├── documents/
│   │   │   ├── hr_leave_policy.md
│   │   │   ├── product_faq.md
│   │   │   └── returns_refund_policy.md
│   │   └── orders.csv             # Source data for orders table
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .dockerignore
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx         # Root HTML layout
│   │   │   ├── page.tsx           # Main chat page (client component)
│   │   │   └── globals.css        # Tailwind + custom styles
│   │   └── components/
│   │       ├── ChatMessage.tsx     # Message bubble + tool info display
│   │       └── ChatInput.tsx       # Input textarea + send button
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── postcss.config.js
│   ├── .dockerignore
│   └── .env.local
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── RUNBOOK.md                      # This file
```

---

## Backend Deep Dive

### Entry Point & API Layer

**File: `backend/app/main.py`**

- Creates the FastAPI application instance.
- Registers CORS middleware (allows all origins for development; restrict in production).
- Mounts the chat router under `/api` prefix.
- Provides a root `/` endpoint with basic API info.

**File: `backend/app/routers/chat.py`**

Two endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST | Main chat endpoint. Accepts `{"message": "..."}`. Returns a `StreamingResponse` that streams tokens. |
| `/api/health` | GET | Health check for Docker/load balancers. Returns `{"status": "healthy"}`. |

The chat endpoint:
1. Gets the singleton `AgentService` instance.
2. Calls `agent.process_question(message)` which is an async generator.
3. Wraps it in a `StreamingResponse` with `text/plain` media type.

---

### Configuration

**File: `backend/app/config.py`**

All settings are loaded from environment variables with sensible defaults:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AWS_AUTH_METHOD` | `sso` | Auth mode: `sso`, `access_keys`, or `iam_role` |
| `AWS_PROFILE` | `default` | AWS SSO profile name |
| `AWS_ACCESS_KEY_ID` | _(empty)_ | For access_keys mode |
| `AWS_SECRET_ACCESS_KEY` | _(empty)_ | For access_keys mode |
| `AWS_DEFAULT_REGION` | `ap-south-1` | AWS region for Bedrock |
| `BEDROCK_MODEL_ID` | `apac.anthropic.claude-3-5-sonnet-20241022-v2:0` | Inference profile ID for Claude |
| `FAISS_INDEX_PATH` | `data/faiss_index` | Where FAISS index is stored |
| `DATABASE_PATH` | `data/orders.db` | SQLite database file |
| `DOCUMENTS_PATH` | `data/documents` | Markdown documents directory |
| `CURRENT_DATE` | `2026-06-15` | Fixed date for time-based queries |

---

### AWS Session Management

**File: `backend/app/services/aws_session.py`**

Factory function `get_aws_session()` returns a `boto3.Session` based on the configured auth method:

- **`sso`**: Uses `profile_name` parameter. Requires `~/.aws/config` and an active SSO session.
- **`access_keys`**: Uses explicit `aws_access_key_id` and `aws_secret_access_key`.
- **`iam_role`**: No credentials passed — boto3 automatically uses the instance metadata service (IMDS) to get temporary credentials from the attached IAM role.

---

### Agent Service (Router)

**File: `backend/app/services/agent.py`**

This is the brain of the system. It:

1. **Routes** the question by calling Claude with a classification prompt.
2. **Executes** the appropriate tool(s).
3. **Streams** the final answer.

#### Routing Logic

The router prompt asks Claude to classify into exactly one of:
- `"rag"` — document/policy questions
- `"sql"` — data/order questions
- `"both"` — mixed questions needing both sources
- `"fallback"` — unrelated questions

Claude responds with JSON: `{"route": "...", "reasoning": "..."}`.

Parsing is defensive — if JSON parsing fails, it tries to extract JSON from the response, and falls back to `"fallback"` if nothing works.

#### Tool Execution

| Route | What happens |
|-------|-------------|
| `rag` | Calls `vector_store.search()` → builds context string → streams Claude answer with RAG prompt |
| `sql` | Calls `_generate_sql()` (Claude generates SQL) → executes against SQLite → streams Claude summary |
| `both` | Runs both RAG retrieval AND SQL generation → streams Claude answer with combined context |
| `fallback` | Returns a static safe message, no LLM call |

#### Prompts (defined as constants in agent.py)

| Prompt | Purpose |
|--------|---------|
| `ROUTER_SYSTEM_PROMPT` | Tells Claude to classify the question |
| `SQL_GENERATION_PROMPT` | Tells Claude to generate SQLite queries (includes schema + date context) |
| `RAG_ANSWER_PROMPT` | Tells Claude to answer from document context with citations |
| `SQL_ANSWER_PROMPT` | Tells Claude to summarize SQL results |
| `BOTH_ANSWER_PROMPT` | Tells Claude to combine both sources |

---

### LLM Service

**File: `backend/app/services/llm.py`**

Wraps AWS Bedrock's `invoke_model` and `invoke_model_with_response_stream` APIs.

Two methods:
- `invoke(system_prompt, user_message)` — Full response (used for routing + SQL generation).
- `stream(system_prompt, user_message)` — Async generator yielding tokens (used for final answers).

Both use the Anthropic Messages API format:
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 2048,
  "system": "...",
  "messages": [{"role": "user", "content": "..."}]
}
```

Streaming parses `content_block_delta` events and yields `text_delta` values.

---

### Vector Store Service

**File: `backend/app/services/vector_store.py`**

#### BedrockEmbeddings Class

Custom LangChain `Embeddings` implementation that calls Bedrock Titan Embed Text v2:
- `embed_documents(texts)` — Embeds a list of texts (used during index building).
- `embed_query(text)` — Embeds a single query (used during search).

Each call sends `{"inputText": "..."}` to `amazon.titan-embed-text-v2:0` and extracts the `"embedding"` array from the response.

#### VectorStoreService Class

On initialization:
1. Checks if a saved FAISS index exists at `FAISS_INDEX_PATH`.
2. If yes → loads it. If no → builds it from documents.

**Index Building:**
1. Loads all `.md` files from `DOCUMENTS_PATH` using LangChain's `DirectoryLoader`.
2. Splits into chunks (500 chars, 50 overlap) using `RecursiveCharacterTextSplitter`.
3. Embeds all chunks via Bedrock Titan.
4. Creates a FAISS index and saves to disk.

**Search:**
1. Embeds the query via Bedrock Titan.
2. Runs similarity search on FAISS index (top-k=4).
3. Returns chunks with source filename and relevance score.

---

### Database Service

**File: `backend/app/services/database.py`**

On initialization:
1. Checks if `orders.db` exists.
2. If not → reads `orders.csv` with pandas and writes to SQLite.

**Methods:**
- `execute_query(sql)` — Only allows SELECT queries. Returns columns, rows as dicts, and row count. Catches errors gracefully.
- `get_schema()` — Returns a human-readable schema string for the LLM (used in SQL generation prompt).

**Safety:** Rejects any query that doesn't start with `SELECT`.

---

## Frontend Deep Dive

### Page & Layout

**File: `frontend/src/app/layout.tsx`**
- Root HTML structure, metadata (title, description), imports global CSS.

**File: `frontend/src/app/page.tsx`**
- Client component (`"use client"`).
- Manages `messages` state (array of user + assistant messages).
- Handles the streaming fetch to `/api/chat`.
- Shows a welcome screen with suggested questions when empty.

### Components

**File: `frontend/src/components/ChatMessage.tsx`**

Renders a single message bubble. For assistant messages, it shows:
- **Tool Badge** — color-coded label (Document Search / Database Query / Both / Out of Scope).
- **Message Content** — rendered as Markdown via `react-markdown`.
- **SQL Query** — expandable `<details>` block showing the generated SQL.
- **Citations** — list of source document filenames.

**File: `frontend/src/components/ChatInput.tsx`**

- Textarea with Enter-to-send (Shift+Enter for newline).
- Send button with loading spinner.
- Disabled state during streaming.

### Streaming Protocol

The frontend reads the response as a stream:

1. **First chunk** (before the first `\n`): JSON metadata object.
   ```json
   {"type": "metadata", "tool_used": "rag", "citations": ["returns_refund_policy.md"]}
   ```
2. **All subsequent chunks**: Raw text tokens from the LLM answer.

The frontend parses the first line as metadata, then concatenates all remaining text into the message content, updating the UI on each chunk for real-time typing effect.

---

## Data Layer

### Documents (Unstructured)

Three Markdown files in `backend/data/documents/`:

| File | Content |
|------|---------|
| `hr_leave_policy.md` | Annual leave (20 days), sick leave (12 days), parental leave, probation rules, application process |
| `product_faq.md` | SmartHub Lite/Pro/Enterprise specs, pricing, setup, warranty, subscription plans |
| `returns_refund_policy.md` | 30-day return window, eligibility, refund process, late returns (15% fee), defective products |

These are chunked (500 chars) and embedded into FAISS on first startup.

### Orders Table (Structured)

**Source:** `backend/data/orders.csv` (45 rows)

| Column | Type | Description |
|--------|------|-------------|
| `order_id` | INTEGER | 1001–1045 |
| `customer` | TEXT | Full name |
| `product` | TEXT | SmartHub Lite / Pro / Enterprise |
| `amount` | REAL | 99.00 / 199.00 / 499.00 |
| `status` | TEXT | delivered / shipped / pending / cancelled |
| `order_date` | TEXT | YYYY-MM-DD format, ranges from 2026-04-10 to 2026-06-15 |

Loaded into SQLite on first startup.

---

## Authentication & AWS Setup

### Option 1: SSO (Local Development)

```bash
# Login
aws sso login --profile default

# Verify
aws sts get-caller-identity --profile default
```

`.env`:
```
AWS_AUTH_METHOD=sso
AWS_PROFILE=default
AWS_DEFAULT_REGION=ap-south-1
```

Docker mounts `~/.aws:/root/.aws:ro` so the container can read SSO cached tokens.

### Option 2: Access Keys

`.env`:
```
AWS_AUTH_METHOD=access_keys
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-south-1
```

No volume mount needed.

### Option 3: EC2/ECS IAM Role (Production)

`.env`:
```
AWS_AUTH_METHOD=iam_role
AWS_DEFAULT_REGION=ap-south-1
```

No credentials needed. The IAM role attached to the EC2 instance or ECS task provides credentials automatically via IMDS.

**Required IAM Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": [
    "arn:aws:bedrock:ap-south-1::foundation-model/amazon.titan-embed-text-v2:0",
    "arn:aws:bedrock:ap-south-1:*:inference-profile/apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
  ]
}
```

---

## Docker & Deployment

### docker-compose.yml

| Service | Image Base | Port | Purpose |
|---------|-----------|------|---------|
| `backend` | `python:3.11-slim` | 8000 | FastAPI server |
| `frontend` | `node:20-alpine` | 3000 | Next.js production server |

**Backend Dockerfile:**
- Slim Python image + `curl` (for healthcheck).
- Installs pip dependencies.
- Copies app code.
- Runs uvicorn.

**Frontend Dockerfile (multi-stage):**
1. `deps` stage: Installs npm packages.
2. `builder` stage: Runs `next build` (produces standalone output).
3. `runner` stage: Minimal Alpine image with just the standalone build. Runs as non-root user.

**Volumes:**
- `~/.aws:/root/.aws:ro` — Read-only mount of AWS credentials (for SSO).
- `faiss_data` — Named volume persisting the FAISS index between container restarts.

### Build & Run

```bash
# Full build
docker-compose up --build

# Rebuild only backend
docker-compose up --build backend

# Detached mode
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down

# Stop and remove volumes (resets FAISS index)
docker-compose down -v
```

### Production Deployment

For deploying to a cloud server:

1. Push to a public GitHub repo.
2. On the server (EC2, etc.):
   ```bash
   git clone <repo>
   cd technova-chatbot
   echo "AWS_AUTH_METHOD=iam_role" > .env
   echo "AWS_DEFAULT_REGION=ap-south-1" >> .env
   docker-compose up -d --build
   ```
3. Attach an IAM role with Bedrock permissions to the instance.
4. Open ports 3000 (frontend) or put behind a reverse proxy (nginx/ALB).

---

## Request Lifecycle (End-to-End)

Here's what happens when a user asks "What was total revenue last month?":

```
1. User types question → clicks Send
2. Frontend: POST /api/chat {"message": "What was total revenue last month?"}
3. Backend (chat.py): Creates StreamingResponse with agent.process_question()
4. Agent: Calls Claude with ROUTER_SYSTEM_PROMPT
   → Claude responds: {"route": "sql", "reasoning": "revenue question needs database"}
5. Agent: Calls Claude with SQL_GENERATION_PROMPT
   → Claude responds: SELECT SUM(amount) as total_revenue FROM orders 
      WHERE order_date BETWEEN '2026-05-01' AND '2026-05-31'
6. Agent: Executes SQL against SQLite
   → Returns: [{"total_revenue": 5765.00}]
7. Agent: Yields metadata JSON: {"type":"metadata","tool_used":"sql","sql_query":"SELECT..."}
8. Agent: Calls Claude STREAM with SQL_ANSWER_PROMPT + results
   → Yields tokens: "The" "total" "revenue" "for" "last" "month" ...
9. Frontend: Parses first chunk as metadata (shows "Database Query" badge)
10. Frontend: Appends subsequent tokens to message content (typing effect)
11. Stream ends → message complete
```

Total LLM calls for this request: **3**
1. Routing classification
2. SQL generation
3. Answer generation (streamed)

---

## Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValidationException: model identifier is invalid` | Wrong model ID for the region | Use inference profile ID (e.g., `apac.anthropic.*`) |
| `ExpiredTokenException` | SSO session expired | Run `aws sso login --profile default` |
| `Container unhealthy` | `curl` not installed or app crash | Check backend logs with `docker-compose logs backend` |
| Frontend shows "Error" | Backend returned 500 | Check backend logs for the stack trace |
| FAISS index errors | Corrupted index | Delete volume: `docker-compose down -v` and restart |
| `node_modules` in Docker context (slow build) | Missing `.dockerignore` | Ensure `.dockerignore` has `node_modules` |
| Wrong AWS account | `AWS_PROFILE` env override | Check `$env:AWS_PROFILE` in your shell |

### Useful Commands

```bash
# Check which AWS account is being used
aws sts get-caller-identity --profile default

# List available Claude models
aws bedrock list-inference-profiles --region ap-south-1 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId,'claude')].[inferenceProfileId]" \
  --output text

# List available embedding models
aws bedrock list-foundation-models --region ap-south-1 \
  --query "modelSummaries[?contains(modelId,'embed')].[modelId]" --output text

# Test backend directly
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the refund window?"}'

# Check container sizes
docker images | grep ai-chatbot
```

---

## Extending the System

### Adding New Documents

1. Add `.md` files to `backend/data/documents/`.
2. Delete the FAISS index: `docker-compose down -v` (or delete `data/faiss_index/` locally).
3. Restart — index rebuilds automatically.

### Adding New Database Tables

1. Add CSV to `backend/data/`.
2. Update `database.py` to load the new table.
3. Update `SQL_GENERATION_PROMPT` in `agent.py` with the new schema.
4. Delete `orders.db` and restart.

### Changing the LLM Model

1. Check available inference profiles: `aws bedrock list-inference-profiles`.
2. Update `BEDROCK_MODEL_ID` in `.env` or `config.py`.
3. Restart.

### Adding Conversation Memory

Currently each question is independent. To add memory:
1. Add a `conversation_id` field to track sessions.
2. Store message history in memory or Redis.
3. Pass conversation history in the Claude messages array.

### Improving the Router

If routing accuracy is poor:
- Add few-shot examples to `ROUTER_SYSTEM_PROMPT`.
- Add a confidence threshold — if routing confidence is low, ask the user to clarify.
- Log routing decisions for analysis.
