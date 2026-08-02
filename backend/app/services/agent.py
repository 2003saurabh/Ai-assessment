import json
import asyncio
import logging
from typing import AsyncGenerator

from app.services.llm import get_llm
from app.services.vector_store import get_vector_store
from app.services.database import get_database
from app.config import settings

logger = logging.getLogger(__name__)

# Combined routing + SQL generation prompt (single Haiku call)
ROUTER_SYSTEM_PROMPT = f"""You are a routing agent and SQL expert for TechNova Inc. Your job is to:
1. Classify the user's question into a category.
2. If the category requires SQL, generate the query immediately.

Categories:
- "rag" — Questions about company policies, product information, HR policies, returns/refund policies, product FAQ. Answered from documents.
- "sql" — Questions about orders, revenue, sales data, customer order history, order counts, order statuses. Requires querying a database.
- "both" — Questions that need BOTH documents AND the orders database.
- "fallback" — Questions completely unrelated to the company's knowledge base.

Database schema (for sql and both routes):
Table: orders
Columns:
- order_id (INTEGER): Unique order identifier
- customer (TEXT): Customer full name
- product (TEXT): Product name (SmartHub Lite, SmartHub Pro, SmartHub Enterprise)
- amount (NUMERIC): Order amount in USD
- status (TEXT): Order status (delivered, shipped, pending, cancelled)
- order_date (DATE): Order date in YYYY-MM-DD format

Important for SQL:
- Current date is {settings.CURRENT_DATE}. Use this for relative date calculations.
- "Last month" = May 2026 (2026-05-01 to 2026-05-31).
- "This month" = June 2026 (2026-06-01 to 2026-06-15).
- Only generate SELECT queries.
- Use PostgreSQL syntax (DATE comparisons, ILIKE for case-insensitive).
- Do NOT use columns that don't exist in the schema.

Respond with ONLY a JSON object:
- If rag: {{"route": "rag"}}
- If sql: {{"route": "sql", "sql_query": "SELECT ..."}}
- If both: {{"route": "both", "sql_query": "SELECT ..."}}
- If fallback: {{"route": "fallback"}}

Do not include any text outside the JSON."""

RAG_ANSWER_PROMPT = """You are a helpful assistant for TechNova Inc. Answer the user's question based ONLY on the provided context documents.

Rules:
- Only use information from the provided context.
- If the context doesn't contain enough information to answer, say so clearly.
- Include citations by referencing the source document name.
- Be concise and accurate.
- Do NOT make up information that isn't in the context.

Context:
{context}

Provide a clear, helpful answer with citations."""

SQL_ANSWER_PROMPT = """You are a helpful assistant for TechNova Inc. Answer the user's question based on the SQL query results.

Rules:
- Summarize the data clearly and concisely.
- If the query returned no results, say so.
- Format numbers nicely (e.g., currency with $ sign).
- Do NOT make up data that isn't in the results.

SQL Query executed:
{sql_query}

Query Results:
{results}

Provide a clear, helpful answer based on these results."""

BOTH_ANSWER_PROMPT = """You are a helpful assistant for TechNova Inc. Answer the user's question using BOTH the document context AND the SQL query results.

Rules:
- Combine information from both sources to give a comprehensive answer.
- Cite document sources when referencing policy information.
- Reference specific data from the query results.
- Be concise and accurate.
- Do NOT make up information.

Document Context:
{context}

SQL Query executed:
{sql_query}

Query Results:
{results}

Provide a clear, comprehensive answer combining both sources."""

FALLBACK_RESPONSE = "I don't have that information. I can only help with questions about TechNova's products, policies (HR leave, returns & refunds), and order data. Please ask me something related to these topics."


class AgentService:
    def __init__(self):
        self.llm = get_llm()
        self.vector_store = get_vector_store()
        self.database = get_database()

    def _route_question(self, question: str) -> dict:
        """Route the question AND generate SQL if needed (single Haiku call)."""
        response = self.llm.invoke(ROUTER_SYSTEM_PROMPT, question, use_fast_model=True)

        # Clean the response — Haiku sometimes puts literal newlines in SQL strings
        # which makes the JSON invalid. Replace newlines inside the response before parsing.
        cleaned = response.strip().replace("\n", " ").replace("\r", " ")

        try:
            route_data = json.loads(cleaned)
            return route_data
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
            return {"route": "fallback"}

    def _get_rag_context(self, question: str) -> tuple[str, list[str]]:
        """Retrieve relevant document chunks."""
        results = self.vector_store.search(question, k=4)

        if not results:
            return "", []

        context_parts = []
        citations = []

        for result in results:
            source = result["source"]
            content = result["content"]
            context_parts.append(f"[Source: {source}]\n{content}")
            if source not in citations:
                citations.append(source)

        return "\n\n---\n\n".join(context_parts), citations

    async def process_question(self, question: str) -> AsyncGenerator[str, None]:
        """Process a question through the agent pipeline with streaming status."""

        # STEP 1: Stream status — Thinking
        yield json.dumps({"type": "status", "message": "Thinking..."}) + "\n"

        # Route + generate SQL in ONE Haiku call
        route_data = self._route_question(question)
        route = route_data.get("route", "fallback")
        sql_query = route_data.get("sql_query")

        # STEP 2: Handle each route
        metadata = {"type": "metadata", "tool_used": route}

        if route == "fallback":
            yield json.dumps(metadata) + "\n"
            yield FALLBACK_RESPONSE
            return

        if route == "rag":
            yield json.dumps({"type": "status", "message": "Searching documents..."}) + "\n"

            context, citations = self._get_rag_context(question)
            metadata["citations"] = citations
            yield json.dumps(metadata) + "\n"

            prompt = RAG_ANSWER_PROMPT.format(context=context)
            async for token in self.llm.stream(prompt, question):
                yield token

        elif route == "sql":
            yield json.dumps({"type": "status", "message": "Querying database..."}) + "\n"

            if not sql_query:
                # Fallback: shouldn't happen, but handle gracefully
                metadata["error"] = "No SQL query generated"
                yield json.dumps(metadata) + "\n"
                yield "I couldn't generate a query for that question. Please try rephrasing."
                return

            sql_clean = sql_query.replace("```sql", "").replace("```", "").strip()
            query_results = self.database.execute_query(sql_clean)
            metadata["sql_query"] = sql_clean

            if query_results.get("error"):
                metadata["error"] = query_results["error"]
                yield json.dumps(metadata) + "\n"
                yield f"I encountered an error executing the query: {query_results['error']}"
                return

            yield json.dumps(metadata) + "\n"

            prompt = SQL_ANSWER_PROMPT.format(
                sql_query=sql_clean,
                results=json.dumps(query_results["results"][:50], indent=2),
            )
            async for token in self.llm.stream(prompt, question):
                yield token

        elif route == "both":
            yield json.dumps({"type": "status", "message": "Searching documents & querying database..."}) + "\n"

            if not sql_query:
                sql_query = ""

            sql_clean = sql_query.replace("```sql", "").replace("```", "").strip()

            # PARALLEL: Run RAG retrieval and SQL execution concurrently
            loop = asyncio.get_event_loop()

            rag_task = loop.run_in_executor(None, self._get_rag_context, question)
            sql_task = loop.run_in_executor(None, self.database.execute_query, sql_clean)

            # Wait for both to complete
            (context, citations), query_results = await asyncio.gather(rag_task, sql_task)

            metadata["citations"] = citations
            metadata["sql_query"] = sql_clean
            yield json.dumps(metadata) + "\n"

            prompt = BOTH_ANSWER_PROMPT.format(
                context=context,
                sql_query=sql_clean,
                results=json.dumps(
                    query_results.get("results", [])[:50], indent=2
                ),
            )
            async for token in self.llm.stream(prompt, question):
                yield token


# Singleton
_agent_service = None


def get_agent() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
