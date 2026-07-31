import json
from typing import AsyncGenerator

from app.services.llm import get_llm
from app.services.vector_store import get_vector_store
from app.services.database import get_database
from app.config import settings

ROUTER_SYSTEM_PROMPT = """You are a routing agent. Your job is to classify a user question into one of these categories:

1. "rag" - Questions about company policies, product information, HR policies, returns/refund policies, product FAQ. These are answered from documents.
2. "sql" - Questions about orders, revenue, sales data, customer order history, order counts, order statuses. These require querying a database.
3. "both" - Questions that need information from BOTH documents AND the orders database. For example, checking if an order qualifies for a policy.
4. "fallback" - Questions that are completely unrelated to the company's knowledge base (e.g., general knowledge, personal opinions, weather).

Respond with ONLY a JSON object in this format:
{"route": "rag"|"sql"|"both"|"fallback", "reasoning": "brief explanation"}

Do not include any other text outside the JSON."""

SQL_GENERATION_PROMPT = f"""You are a SQL expert. Generate a SQLite query based on the user's question.

Database schema:
Table: orders
Columns:
- order_id (INTEGER): Unique order identifier
- customer (TEXT): Customer full name
- product (TEXT): Product name (SmartHub Lite, SmartHub Pro, SmartHub Enterprise)
- amount (REAL): Order amount in USD
- status (TEXT): Order status (delivered, shipped, pending, cancelled)
- order_date (TEXT): Order date in YYYY-MM-DD format

Important:
- The current date is {settings.CURRENT_DATE}. Use this for relative date calculations.
- "Last month" means May 2026 (2026-05-01 to 2026-05-31).
- "This month" means June 2026 (2026-06-01 to 2026-06-15).
- Only generate SELECT queries.
- Do NOT use columns that don't exist in the schema.

Respond with ONLY the SQL query, no explanation or markdown formatting."""

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
        """Determine which tool to use for the question."""
        response = self.llm.invoke(ROUTER_SYSTEM_PROMPT, question)

        try:
            # Try to parse the JSON response
            route_data = json.loads(response.strip())
            return route_data
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    pass
            return {"route": "fallback", "reasoning": "Could not parse routing response"}

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

    def _generate_sql(self, question: str) -> str:
        """Generate SQL query from the question."""
        return self.llm.invoke(SQL_GENERATION_PROMPT, question).strip()

    async def process_question(self, question: str) -> AsyncGenerator[str, None]:
        """Process a question through the agent pipeline with streaming."""
        # Step 1: Route the question
        route_data = self._route_question(question)
        route = route_data.get("route", "fallback")

        # Emit metadata as first chunk
        metadata = {"type": "metadata", "tool_used": route}

        if route == "fallback":
            metadata["answer_preview"] = FALLBACK_RESPONSE
            yield json.dumps(metadata) + "\n"
            yield FALLBACK_RESPONSE
            return

        if route == "rag":
            context, citations = self._get_rag_context(question)
            metadata["citations"] = citations
            yield json.dumps(metadata) + "\n"

            prompt = RAG_ANSWER_PROMPT.format(context=context)
            async for token in self.llm.stream(prompt, question):
                yield token

        elif route == "sql":
            sql_query = self._generate_sql(question)
            # Clean SQL query (remove markdown code blocks if present)
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
            # Get both sources
            context, citations = self._get_rag_context(question)
            sql_query = self._generate_sql(question)
            sql_clean = sql_query.replace("```sql", "").replace("```", "").strip()
            query_results = self.database.execute_query(sql_clean)

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
