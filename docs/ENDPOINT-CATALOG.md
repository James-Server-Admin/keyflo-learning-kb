# Endpoint catalog — learning KB (KeyFlo org pointer)

**Agents:** Full endpoint specs live in **`KeyFlo-ai/kb-gateway` → [`docs/ENDPOINT-CATALOG.md`](https://github.com/KeyFlo-ai/kb-gateway/blob/main/docs/ENDPOINT-CATALOG.md)**.

Quick reference:

| Need | MCP tool | HTTP |
|------|----------|------|
| Broad research / "what do we know?" | `query_all` | `POST /v1/query` default |
| Unsure graph vs vector | `route_query` | `POST /v1/query` with `all_namespaces=false` |
| Passages (courses) | `query_namespace` → `course-transcripts` | — |
| Passages (patterns) | `query_namespace` → `patterns` | — |
| LangChain docs | `query_namespace` → `langchain-docs` | — |
| Coverage / lanes | `graph_query` mode=`lane`\|`topics`\|`stats` | — |
| Disputes | `graph_query` mode=`disputes` | `route_query` / `POST /v1/query` with `all_namespaces=false` |
| Inventory | `list_namespaces` | — |

**MCP:** `https://kb-mcp.waytie.com/mcp` · setup: [`COLE-SETUP.md`](COLE-SETUP.md)  
**HTTP:** `https://kb-api.keyflo.ai` · [`docs/public-api.md`](public-api.md)

Corpus: Pinecone `learning` (93k+ transcript vectors) + Neo4j (116 courses, 462 topics). See endpoint catalog §1 for live counts.
