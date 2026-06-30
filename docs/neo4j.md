# Neo4j knowledge graph — READ-ONLY access guide

**Audience:** Cole and collaborators querying the **learning knowledge graph**.  
**Container:** `learning-kg-neo4j` · **Bolt:** `bolt://localhost:7689` (server-local; not exposed to the internet).  
**Access model: READ ONLY** — MATCH queries only; no CREATE, MERGE, SET, or DELETE.

---

## What this graph is

A Neo4j knowledge graph built over the same **learning corpus** indexed in Pinecone (`learning` / `course-transcripts`). It answers structural questions vectors cannot:

| Question type | Graph capability |
|---|---|
| Coverage | Which topics exist, how many lectures / courses cover each |
| Depth | Lecture count per topic (atomic instruction units) |
| Breadth | Course count per topic (independent sources) |
| Disputes | Cross-course contradictions (`Claim`—`CONTRADICTS`—`Claim` edges) |
| Topology | Course → Lecture → Topic relationships |

**Approximate scale:** 116 courses · 18,255 lectures · 462 topics · 106 disciplines · 290 claims.

Pinecone holds the **text**; Neo4j holds the **map**. Use both (see [`routing.md`](routing.md)).

---

## Access keys (operator-issued — never in this repo)

Three environment variables (James provides via secure channel):

| Variable | Purpose |
|---|---|
| `LEARNING_KG_NEO4J_URI` | Bolt URI, e.g. `bolt://localhost:7689` |
| `LEARNING_KG_NEO4J_USER` | Username (typically `neo4j`) |
| `LEARNING_KG_NEO4J_PASSWORD` | Password |

On the Keyflo server, these live in `/mnt/blockstorage/env/global.env`. For local/script use:

```bash
export LEARNING_KG_NEO4J_URI=bolt://...
export LEARNING_KG_NEO4J_USER=neo4j
export LEARNING_KG_NEO4J_PASSWORD=...
```

**Remote access:** The graph runs on James's server only. Cole queries via SSH to the server, or James runs queries on request. There is no public Neo4j endpoint.

---

## CLI queries (recommended)

[`scripts/query_graph.py`](../scripts/query_graph.py) wraps read-only Cypher — no writes by construction.

```bash
pip install neo4j

python scripts/query_graph.py --stats
python scripts/query_graph.py --lane copy
python scripts/query_graph.py --lane design
python scripts/query_graph.py --lane campaign
python scripts/query_graph.py --topics "headline persuasion email"
python scripts/query_graph.py --topics "langsmith tracing"   # multi-surface: topic + narrow + discipline + lecture
python scripts/query_graph.py --disputes
```

`--topics` searches **four surfaces** (fixes lexical label gap where Topic cluster labels miss product-specific terms like LangSmith):

| Surface | What it matches |
|---|---|
| `topic` | Emergent Topic cluster labels |
| `narrow` | External-ontology sub-skills (e.g. LLMOps / observability) |
| `discipline` | Reference-frame disciplines |
| `lecture` | Lecture titles (ranked by keyword specificity) |

Output: grouped rows per surface — topic/narrow/discipline counts, or course + title for lectures.

---

## Example Cypher (read-only)

If you use `cypher-shell` on the server:

```cypher
// Top copy-related topics by lecture depth
MATCH (l:Lecture)-[:COVERS]->(t:Topic)
WHERE NOT t:Admin
  AND any(kw IN ['copy','headline','persuasion']
          WHERE toLower(t.label) CONTAINS kw)
RETURN t.domain AS domain, t.label AS topic,
       count(DISTINCT l) AS lectures,
       count(DISTINCT l.course) AS courses
ORDER BY lectures DESC LIMIT 10;
```

```cypher
// Marketing disputes
MATCH (a:Claim)-[r:CONTRADICTS]->(b:Claim)
WHERE a.course <> b.course AND r.confidence >= 0.6
  AND (a.domain IN ['marketing','sales'] OR b.domain IN ['marketing','sales'])
RETURN r.confidence AS confidence,
       a.course AS course_a, a.statement AS claim_a,
       b.course AS course_b, b.statement AS claim_b
ORDER BY r.confidence DESC LIMIT 5;
```

```cypher
// Corpus health check
MATCH (c:Course) WITH count(c) AS courses
MATCH (l:Lecture) WITH courses, count(l) AS lectures
MATCH (t:Topic) WHERE NOT t:Admin WITH courses, lectures, count(t) AS topics
RETURN courses, lectures, topics;
```

---

## Node types (mental model)

```
Course ──has──▶ Lecture ──COVERS──▶ Topic
                                      ▲
Claim ──CONTRADICTS──▶ Claim         (topics cluster lectures)
Discipline (cross-cutting taxonomy)
```

- **Topic** — canonical label (e.g. "StoryBrand Framework", "Facebook Ads Targeting")
- **Lecture** — one transcript chunk's source lecture; carries `course` property
- **Claim** — extracted assertion; disputes link claims across courses

---

## Marketing pipeline integration

Pipeline code never writes to the graph. It imports:

```
pipeline/lib/kg_conn.py   → read-only driver
pipeline/lib/kg_queries.py → marketing-scoped Cypher
pipeline/lib/kg_research.py → kg_ground() GraphRAG entry point
```

See `keyflo-marketing/pipeline/lib/README-kg.md` for the agent contract (citation requirements, 30-lecture floor, dispute handling).

Verify connectivity on server:

```bash
cd /root/langchain-course && ./run runtime/agentic_router.py --help 2>/dev/null || true
python /path/to/knowledge-base/scripts/query_graph.py --stats
```

---

## Ground rules

- **Read-only only.** Corrections and re-ingest are operator workflows in `langchain-course/graph/`.
- **Server-local.** Bolt port 7689 is not internet-facing.
- **Isolated from other businesses.** `vetriq-neo4j` (7687) and `serverorg-neo4j` (7688) are separate — do not query them for Keyflo marketing corpus questions.
- Disputes are rare for straight marketing technique; when `dispute_flags` appear in pipeline output, do not assert contested claims without softening or operator review.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ServiceUnavailable` / connection refused | Container down | Operator: `docker ps \| grep learning-kg-neo4j` → `docker start learning-kg-neo4j` |
| Missing env var error | Credentials not exported | Load from James or `source /mnt/blockstorage/env/load.sh` on server |
| Empty dispute results | Normal for many topics | Disputes exist on ~6 of 410 topics; use `--disputes` or agentic router for dispute-shaped questions |
| Topic counts seem stale | Corpus re-ingested without graph rebuild | Operator rebuild via `langchain-course/graph/` pipeline; do not trust coverage until rebuilt |
