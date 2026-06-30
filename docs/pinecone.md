# Pinecone vector index — READ-ONLY access

**Index:** `learning` · **Embedding model:** `text-embedding-3-large` (3072-dim, immutable)

See also: [`routing.md`](routing.md) · [`../AGENTS.md`](../AGENTS.md)

---

## Namespaces (in-scope)

| Namespace | Contains | Example questions |
|---|---|---|
| `patterns` | Proven process/engineering patterns | "How should I structure a PR review?" |
| `course-transcripts` | Udemy-style lectures: marketing, PM, git | "Facebook ads campaign structure" |
| `langchain-docs` | LangChain / LangGraph / LangSmith docs | "How do I use LangGraph state?" |
| `research-papers` | External papers / whitepapers | "What research papers cover RAG eval?" |

**Do not query:** `own-notes`, `orchestrations` — internal operator records.

**Operator/local targeted namespaces:** `pinecone-platform` for Pinecone
templates/runbooks and `platform-fabric` for fabric governance. These are
available through the local CLI when server credentials are loaded; they are not
guaranteed for every remote collaborator.

---

## Access keys (operator-issued — never in this repo)

1. **`LEARNING_PINECONE_API_KEY`** — read-only key for the Pinecone project owning index `learning` (scripts map this → `PINECONE_API_KEY` automatically)
2. **`OPENAI_API_KEY`** — embeds your question before search

James provides both via secure channel. Set as environment variables only.

On server: `source /mnt/blockstorage/env/load.sh` loads all keys. The CLIs also auto-read `/mnt/blockstorage/env/global.env` when present.

**Do not** point `PINECONE_API_KEY` at the legacy global key — it targets a different Pinecone project and returns 404 on index `learning`.

---

## Query CLI

```bash
pip install -r requirements.txt
export LEARNING_PINECONE_API_KEY=...   # read-only, from James
export OPENAI_API_KEY=...

python scripts/query_db.py "how should final ad assets be separated from drafts?"
python scripts/query_db.py --namespace course-transcripts --k 8 "facebook ads campaign structure"
python scripts/query_db.py --namespace patterns "phase gate before merge"
```

Output: top matches with similarity scores + source file citations.

---

## When to use Pinecone vs Neo4j

| Use Pinecone when… | Use Neo4j instead when… |
|---|---|
| "How do I X?" / semantic how-to | "Which courses cover X?" |
| Find passages like a topic | Coverage gaps, topic depth counts |
| Process patterns (`patterns` ns) | Cross-course **disputes** |
| Broad research / "what do we know?" | Use MCP `query_all` or HTTP `/v1/query` default |
| | Not sure graph vs vector → [`scripts/route_query.py`](../scripts/route_query.py) |

---

## Ground rules

- Results are reference material — confirm operational changes with operator.
- Absence/not-covered claims require a healthy full-corpus query plus graph/coverage checks; one namespace or one router result is not enough.
- Never commit or share API keys.
- Stale content → report to operator; corrections go through ingest pipeline.
