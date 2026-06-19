# Router source (reference copy)

This file is a **reference copy** of the agentic router from [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course).

**Execution:** The router requires langchain-course runtime dependencies (LangGraph, Pinecone, Neo4j driver, rigorous_benchmark, retrieval grader, etc.). On the Keyflo server, run via:

```bash
python scripts/route_query.py "your question"
# or directly:
cd /root/langchain-course && ./run runtime/agentic_router.py "your question"
```

**Public API:** `route_query(question: str, k: int = 6, max_retries: int = 2) -> dict`

Returns: `answer`, `route`, `route_reason`, `graph_context`, `source_documents`, `structured_response`, `retries`.

**Docs:** [`../docs/agentic-router.md`](../docs/agentic-router.md) · [`../AGENTS.md`](../AGENTS.md)

When updating the router, sync this copy from `langchain-course/runtime/agentic_router.py`.
