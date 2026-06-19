# keyflo-learning-kb

**Canonical Keyflo org repo** for querying the learning corpus and routing between Pinecone and Neo4j.

| Audience | Start here |
|---|---|
| **LLMs / agents** | [`AGENTS.md`](AGENTS.md) |
| **Humans (Cole, collaborators)** | This README + [`docs/routing.md`](docs/routing.md) |
| **Discovery index** | [`llms.txt`](llms.txt) |

## Cole / collaborator handoff

1. **Clone this repo** (you need `KeyFlo-ai` org access):
   ```bash
   git clone git@github.com:KeyFlo-ai/keyflo-learning-kb.git
   cd keyflo-learning-kb
   ```
2. **Point your agent at** [`AGENTS.md`](AGENTS.md) — routing table, tools, boundaries, checklist.
3. **Run queries on the Keyflo server** (Neo4j is server-local; not reachable from a laptop):
   ```bash
   ssh <keyflo-server>
   git clone git@github.com:KeyFlo-ai/keyflo-learning-kb.git
   cd keyflo-learning-kb
   pip install -r requirements.txt
   source /mnt/blockstorage/env/load.sh global   # or use read-only keys James sends you
   ```
4. **Router runtime** also needs [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course) at `/root/langchain-course` on the server (already installed for operators).

Ask James for read-only `LEARNING_PINECONE_API_KEY`, `LEARNING_KG_NEO4J_*`, and `OPENAI_API_KEY` if you are not using the server env loader.

## What's in this repo

The learning corpus (~116 courses, marketing + engineering patterns) lives in **two read-only stores** on the Keyflo server:

| Store | Technology | Best for |
|---|---|---|
| **Vector** | Pinecone index `learning` | Semantic search, how-to passages |
| **Graph** | Neo4j `learning-kg-neo4j` | Coverage, topic depth, cross-course disputes |

**Agentic router** — when you're not sure which to use, `scripts/route_query.py` classifies the question and retrieves from the right store(s). Source: [`router/agentic_router.py`](router/agentic_router.py).

## Quick start (server)

Credentials from James (never committed). On the Keyflo server:

```bash
git clone git@github.com:KeyFlo-ai/keyflo-learning-kb.git
cd keyflo-learning-kb
pip install -r requirements.txt
source /mnt/blockstorage/env/load.sh global   # operator env

# Not sure which DB → use the router
python scripts/route_query.py "how do I structure a Meta lead gen campaign?"

# Know you need vectors
python scripts/query_db.py --namespace course-transcripts "PAS headline formulas"

# Know you need graph structure
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

## Related repos

- [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course) — full runtime, ingest, graph build (router executes here on server)
- [`KeyFlo-ai/keyflo-marketing`](https://github.com/KeyFlo-ai/keyflo-marketing) — `kg_ground()` for ad pipeline GraphRAG

## Access model

**READ ONLY.** Query and cite; never write to Pinecone or Neo4j from this repo.
