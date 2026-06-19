# Agentic router — automatic graph ↔ vector routing

**Audience:** Cole and operators asking **open-ended questions** against the learning corpus.  
**Implementation:** [`router/agentic_router.py`](../router/agentic_router.py) (this repo) · runtime [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course)  
**Entry point:** `route_query(question, k=6, max_retries=2)`

When you are not sure whether to query Pinecone or Neo4j, **use this agent**. It classifies the question, retrieves from the right store(s), grades context, self-corrects (widens search if needed), and returns an answer with citations.

---

## What it does

```
START → route (LLM picks: vector | graph | both)
      → retrieve (Pinecone passages and/or Neo4j structural facts)
      → grade (relevance filter)
      → (good enough?) ─ yes → answer
                     └ no  → widen k → retrieve (retry, max 2)
      → END
```

| Route | Retrieves from | Unique value |
|---|---|---|
| `vector` | Pinecone `course-transcripts` + rerank | Semantic passages, how-to detail |
| `graph` | Neo4j topic coverage + disputes + K1 chunk drill-down | Structural facts vectors cannot produce |
| `both` | Graph facts prepended + RRF-fused vector+graph sources | Synthesis answers with honest structure |

The router operationalizes the pattern in `langchain-course/patterns/proven/kg-vector-routing.md`.

---

## How to run (Keyflo server)

The router needs **server access** — Neo4j (7689), Pinecone, OpenAI, and LangSmith env from `global.env`.

### This repo (Keyflo server)

```bash
cd keyflo-learning-kb
source /mnt/blockstorage/env/load.sh global
python scripts/route_query.py "do any courses disagree about how to open a negotiation?"
python scripts/route_query.py --k 8 "how do I structure a Meta lead gen campaign?"
```

### Direct (langchain-course repo)

```bash
cd /root/langchain-course
./run runtime/agentic_router.py "your question here"
./run runtime/agentic_router.py --k 8 "your question"
```

Example output:

```
ROUTE: graph  (question asks about cross-course disagreement)

GRAPH CONTEXT:
DISPUTE (claim): Course A says "..." — but Course B says "..."

ANSWER:
[structured answer with confidence + sources]

sources: ['238-social-media-design-niche.md', ...] | retries: 0
```

---

## When to use vs manual CLIs

| Situation | Use |
|---|---|
| Not sure which store | **Agentic router** |
| Know you need passages only | `query_db.py` |
| Know you need coverage/disputes only | `query_graph.py` |
| Marketing pipeline stage (copy/creative) | `kg_ground(lane=...)` — see [`../pipeline/lib/README-kg.md`](../pipeline/lib/README-kg.md) |
| Keyflo product positioning / homepage claims | Qdrant `keyflo_source_of_truth` — **not** this corpus |

Routing decision table: [`routing.md`](routing.md).

---

## Route classifier (how it decides)

The routing LLM uses these definitions (from `agentic_router.py`):

- **graph** — COVERAGE ("what does the corpus cover"), DISPUTES ("do sources disagree"), STRUCTURE ("which courses cover X", "how do topics relate")
- **vector** — specific / how-to / factual ("how do I X", "what is X", "explain X")
- **both** — broad synthesis wanting answer + structural context

Example mappings:

| Question | Expected route |
|---|---|
| "Do any courses disagree about opening negotiations?" | `graph` |
| "How do I write a benefit-led headline?" | `vector` |
| "Best Meta campaign structure for B2B services — what does the corpus cover?" | `both` |

---

## Python API (for scripts)

On the server with `langchain-course` on the path:

```python
import sys
sys.path.insert(0, "/root/langchain-course")

from runtime.agentic_router import route_query

result = route_query("which courses cover StoryBrand?", k=6)
print(result["route"], result["route_reason"])
print(result["graph_context"])
print(result["answer"])
print(result["source_documents"])
```

Return dict keys: `answer`, `route`, `route_reason`, `graph_context`, `source_documents`, `structured_response`, `retries`.

---

## LangSmith tracing

Runs trace as `agentic_router` in LangSmith project `LANGCHAIN-APP`. Each node (`route`, `retrieve`, `grade`, `answer`) is a child span. Useful for debugging mis-routes or empty retrieval.

---

## Limitations

- **Server-only** — requires local Neo4j + env files; GitHub Actions cloud runners cannot reach the graph.
- **Not latency-optimized** — `both` route runs graph + vector + 2+ LLM calls.
- **Learning corpus only** — personal-accumulation layer; not Keyflo product KB or VETRIQ data.
- **No auto-retry on OpenAI 429** — re-run manually if rate-limited.

Full operator runbook (failure modes, alerts):  
`langchain-course/docs/runbooks/agentic-router.md`

---

## Related: marketing pipeline GraphRAG

The ad pipeline uses a **lighter** combined retrieval — `kg_ground()` in `pipeline/lib/kg_research.py`:

1. Neo4j ranks topics for a lane (`copy`, `design`, `campaign`, `tracking`)
2. Pinecone fetches lecture chunks guided by the top topic label
3. Result feeds copy generation and creative grounding

That path is lane-scoped and citation-audited for pipeline artifacts. The agentic router is for **ad-hoc Q&A**, not gated pipeline output.
