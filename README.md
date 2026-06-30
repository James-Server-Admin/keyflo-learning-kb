# knowledge-base

HTTP/API companion repo (`KeyFlo-ai/knowledge-base`) for James's learning corpus.
The canonical remote agent gateway is `James-Server-Admin/kb-gateway` with MCP
tool `answer_learning_kb`; this repo remains the simple HTTP fallback and local
CLI documentation.

| Audience | Start here |
|---|---|
| **Cole / collaborators** | [`docs/COLE-SETUP.md`](docs/COLE-SETUP.md) |
| **LLMs / agents** | [`AGENTS.md`](AGENTS.md) |
| **Discovery index** | [`llms.txt`](llms.txt) |

## Dual GitHub hosts (both kept)

| Host | Repo | Use when |
|---|---|---|
| **KeyFlo org** | `KeyFlo-ai/knowledge-base` | Cole / Keyflo collaborators with org access |
| **External mirror** | `James-Server-Admin/keyflo-learning-kb` | Access from outside KeyFlo org (public clone, no org membership) |

Both repos stay in sync. Operator refresh:

```bash
/mnt/blockstorage/private/credentials/scripts/sync-knowledge-base-gh-secrets.sh   # secrets on both
./scripts/publish-to-keyflo-org.sh                                              # push code to both
```

## Cole — start here

Full handoff: **[`docs/COLE-SETUP.md`](docs/COLE-SETUP.md)** (clone, bearer token, query CLI, optional SSH/Actions).

**Fast path (no SSH):**

```bash
git clone git@github.com:KeyFlo-ai/knowledge-base.git && cd knowledge-base
gh auth login
./scripts/setup-cole-env.sh
source config/cole.env
python scripts/query_api.py "which courses cover copywriting?"
```

Give your coding agent [`AGENTS.md`](AGENTS.md). MCP-capable agents should use
`answer_learning_kb` from `https://kb-mcp.waytie.com/mcp`; use this HTTP API
when MCP is unavailable. HTTP API reference: [`docs/public-api.md`](docs/public-api.md).

## What's in this repo

James's learning corpus (~116 courses across business, tech, finance, creative, ops, engineering, marketing, plus patterns and research papers where available) lives in **two read-only stores** on the server:

| Store | Technology | Best for |
|---|---|---|
| **Vector** | Pinecone index `learning` | Semantic search, how-to passages |
| **Graph** | Neo4j `learning-kg-neo4j` | Coverage, topic depth, cross-course disputes |

**Default broad query** — the HTTP API runs full-corpus retrieval by default. For
agents, prefer the gateway `answer_learning_kb` contract because it returns
retrieval status, evidence sources, cautions, and next steps. Use
`scripts/route_query.py` when graph-vs-vector routing or structural synthesis
matters. Source: [`router/agentic_router.py`](router/agentic_router.py).

## Quick start (server SSH — optional)

```bash
git clone git@github.com:KeyFlo-ai/knowledge-base.git
cd knowledge-base
pip install -r requirements.txt
source /mnt/blockstorage/env/load.sh

python scripts/route_query.py "how do I structure a Meta lead gen campaign?"
python scripts/query_db.py --namespace course-transcripts "PAS headline formulas"
python scripts/query_graph.py --lane copy
python scripts/query_graph.py --disputes
```

## Documentation

| Doc | Topic |
|---|---|
| [`docs/COLE-SETUP.md`](docs/COLE-SETUP.md) | **Cole handoff** — token, CLI, GitHub secrets |
| [`docs/routing.md`](docs/routing.md) | **Which database when** |
| [`docs/public-api.md`](docs/public-api.md) | **HTTP API** (no SSH) |
| [`docs/pinecone.md`](docs/pinecone.md) | Pinecone access |
| [`docs/neo4j.md`](docs/neo4j.md) | Neo4j access |
| [`docs/agentic-router.md`](docs/agentic-router.md) | Router agent |

## Public HTTP API

| Endpoint | Auth |
|----------|------|
| `GET https://kb-api.keyflo.ai/health` | none |
| `POST https://kb-api.keyflo.ai/v1/query` | Bearer token from James |

```bash
python scripts/query_api.py "which courses cover copywriting?"
```

Operator deploy: [`docs/public-api.md`](docs/public-api.md) · `deploy/` · `scripts/run-api.sh`

## Related repos

- [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course) — full runtime, ingest, graph build (router executes here on server)
- [`KeyFlo-ai/keyflo-marketing`](https://github.com/KeyFlo-ai/keyflo-marketing) — `kg_ground()` for ad pipeline GraphRAG

## Access model

**READ ONLY.** Query and cite; never write to Pinecone or Neo4j from this repo.

## Operator: publish / refresh GitHub secrets

```bash
/mnt/blockstorage/private/credentials/scripts/sync-knowledge-base-gh-secrets.sh
# or from this repo:
./scripts/publish-to-keyflo-org.sh --secrets-only
```

First-time repo + push: `./scripts/publish-to-keyflo-org.sh`
