# knowledge-base

**Canonical Keyflo org repo** (`KeyFlo-ai/knowledge-base`) for querying the learning corpus and routing between Pinecone and Neo4j.

| Audience | Start here |
|---|---|
| **LLMs / agents** | [`AGENTS.md`](AGENTS.md) |
| **Humans (Cole, collaborators)** | This README + [`docs/routing.md`](docs/routing.md) |
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

## Cole / collaborator handoff

1. **Clone** (pick host):
   ```bash
   # KeyFlo org member:
   git clone git@github.com:KeyFlo-ai/knowledge-base.git
   # Outside KeyFlo org:
   git clone https://github.com/James-Server-Admin/keyflo-learning-kb.git
   cd knowledge-base   # or keyflo-learning-kb — same content
   ```
2. **Point your agent at** [`AGENTS.md`](AGENTS.md) — routing table, tools, boundaries, checklist.
3. **GitHub runtime:** Settings → Actions → **Variables** (`COLE_SETUP`, server host, paths) and **Secrets** (`LEARNING_KB_COLE_RUNTIME` + individual keys). Run **smoke-query** workflow when the self-hosted runner is registered.
4. **Run queries on the Keyflo server** (Neo4j is server-local):
   ```bash
   ssh root@192.241.169.31
   git clone git@github.com:KeyFlo-ai/knowledge-base.git && cd knowledge-base
   pip install -r requirements.txt
   source /mnt/blockstorage/env/load.sh   # or read-only keys from James
   python scripts/route_query.py "which courses cover copywriting?"
   ```
5. **Router runtime** also needs [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course) at `/root/langchain-course` on the server.

## What's in this repo

The learning corpus (~116 courses, marketing + engineering patterns) lives in **two read-only stores** on the Keyflo server:

| Store | Technology | Best for |
|---|---|---|
| **Vector** | Pinecone index `learning` | Semantic search, how-to passages |
| **Graph** | Neo4j `learning-kg-neo4j` | Coverage, topic depth, cross-course disputes |

**Agentic router** — when you're not sure which to use, `scripts/route_query.py` classifies the question and retrieves from the right store(s). Source: [`router/agentic_router.py`](router/agentic_router.py).

## Quick start (server)

```bash
git clone git@github.com:KeyFlo-ai/knowledge-base.git
cd knowledge-base
pip install -r requirements.txt
source /mnt/blockstorage/env/load.sh global

python scripts/route_query.py "how do I structure a Meta lead gen campaign?"
python scripts/query_db.py --namespace course-transcripts "PAS headline formulas"
python scripts/query_graph.py --lane copy
python scripts/query_graph.py --disputes
```

## Documentation

| Doc | Topic |
|---|---|
| [`docs/routing.md`](docs/routing.md) | **Which database when** |
| [`docs/pinecone.md`](docs/pinecone.md) | Pinecone access |
| [`docs/neo4j.md`](docs/neo4j.md) | Neo4j access |
| [`docs/agentic-router.md`](docs/agentic-router.md) | Router agent |
| [`docs/public-api.md`](docs/public-api.md) | **HTTP API** (Cole without SSH) |

## Public HTTP API (no SSH)

Bearer-authenticated read-only gateway on the Keyflo server:

```bash
# Server operator
./scripts/run-api.sh   # 127.0.0.1:8791

# Cole (after James sends a token)
curl -s https://kb-api.keyflo.ai/v1/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"which courses cover copywriting?"}'
```

See [`docs/public-api.md`](docs/public-api.md) for systemd, nginx, and Cloudflare setup.

## Related repos

- [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course) — full runtime, ingest, graph build (router executes here on server)
- [`KeyFlo-ai/keyflo-marketing`](https://github.com/KeyFlo-ai/keyflo-marketing) — `kg_ground()` for ad pipeline GraphRAG

## Access model

**READ ONLY.** Query and cite; never write to Pinecone or Neo4j from this repo.

## Operator: publish / refresh GitHub secrets

Canonical sync (operator gh auth on `KeyFlo-ai/knowledge-base`):

```bash
/mnt/blockstorage/private/credentials/scripts/sync-knowledge-base-gh-secrets.sh
# or from this repo:
./scripts/publish-to-keyflo-org.sh --secrets-only
```

First-time repo + push: `./scripts/publish-to-keyflo-org.sh`
