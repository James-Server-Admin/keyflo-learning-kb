# Which database to query — routing guide

**Audience:** Cole, agents, and pipeline authors.  
**Canonical repo:** `KeyFlo-ai/knowledge-base` (this documentation).  
**Router implementation:** [`router/agentic_router.py`](../router/agentic_router.py) (reference) · runtime in [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course).  
**Marketing pipeline GraphRAG:** `kg_ground()` in [`KeyFlo-ai/keyflo-marketing`](https://github.com/KeyFlo-ai/keyflo-marketing) · `pipeline/lib/kg_research.py`.

---

## Decision table

| Your question looks like… | Route | Tool |
|---|---|---|
| "How do I X?" / "Explain X" / "Find content like X" | **Vector (Pinecone)** | `scripts/query_db.py --namespace course-transcripts` |
| "What's the routine for Y?" / process patterns | **Vector (Pinecone)** | `scripts/query_db.py --namespace patterns` |
| "Which courses cover topic X?" | **Graph (Neo4j)** | `scripts/query_graph.py --topics "X"` |
| "What does the corpus cover / not cover?" | **Graph (Neo4j)** | `scripts/query_graph.py --lane <lane>` |
| "Do any courses **disagree** about X?" | **Graph (Neo4j)** | `scripts/query_graph.py --disputes` or `scripts/route_query.py` |
| "How do topics relate?" / multi-hop structure | **Graph (Neo4j)** | `scripts/route_query.py` (route=graph) |
| Broad synthesis ("best approach to X considering the full corpus") | **Both** | `scripts/route_query.py "..."` |
| Marketing copy / creative / campaign grounding (pipeline) | **Both (GraphRAG)** | `kg_ground(question, lane="copy")` |

---

## Why two stores?

Vectors return **passages that look like your question**. The graph returns **structure the vectors cannot see**:

1. **Disagreements** — "Do courses disagree about X?" is a `CONTRADICTS` edge in Neo4j, not an embedding. Vector-only RAG often returns passages from both sides and says "no disagreement" — confidently wrong.
2. **Coverage** — "Which courses cover X?" from vector metadata names whatever course field appeared on returned chunks, which is often wrong. The graph walks `Lecture→COVERS→Topic` and counts distinct courses reliably.

The agentic router backtest showed vector-only **hallucinates structural claims ~25–33%** of the time on coverage/dispute questions; the router grounded in graph edges **0%**.

---

## Route definitions (agent classifier)

These match the LLM classifier in `agentic_router.py`:

### `vector` — Pinecone

Use for: specific, semantic, how-to, factual passage questions.

Examples:
- "How do I write a PAS headline?"
- "What is RRF in hybrid search?"
- "Scroll-stopping ad image contrast techniques"

### `graph` — Neo4j

Use for: coverage, gaps, disputes, structure, multi-hop.

Examples:
- "Which courses cover StoryBrand?"
- "Do any courses disagree about how to open a negotiation?"
- "What marketing topics have the most lecture depth?"

### `both` — Graph facts + vector passages

Use for: broad questions wanting an answer **plus** structural context.

Examples:
- "What's the best approach to Meta lead gen for professional services?"
- "How should I structure a campaign, and what does the corpus actually cover on targeting?"

Flow: graph returns topic coverage + disputes as prepended facts → vector returns ranked lecture passages → grader filters → LLM answers.

---

## Marketing pipeline lanes (Neo4j keywords)

When calling `kg_ground()`, pick a **lane** — each maps to curated graph keywords:

| Lane | Keywords (sample) | Use for |
|---|---|---|
| `copy` | copy, headline, storytelling, persuasion, email, writing | Hero, benefits, primary text |
| `design` | design, creative, image, visual, scroll, contrast | Ad creative variants |
| `campaign` | campaign, ad set, budget, audience, targeting, objective | Campaign structure, audiences |
| `tracking` | conversion, tracking, pixel, remarketing, attribution | Pixel binds, attribution |

```python
from pipeline.lib.kg_research import kg_ground

g = kg_ground("hero headline for OK real estate agents", lane="copy", elements=["hero"])
# g["covered_topics"]  — graph-ranked topics
# g["content_evidence"] — Pinecone lecture chunks (GraphRAG drill-down)
```

Contract details: `keyflo-marketing/pipeline/lib/README-kg.md`.

---

## GraphRAG pattern (pipeline default)

```
Question + lane
    │
    ▼
Neo4j: covered_for_lane(lane) + question tokens → ranked topics
    │
    ▼
Pinecone: retrieve_content(question, topic_hint=top_topic) → lecture chunks
    │
    ▼
Combined grounding record (citations + content_evidence + disputes)
```

This is simpler than the full agentic router but follows the same division of labour: **graph scopes, vector fetches content**.

---

## When NOT to use the router

- **Latency-critical hot paths** — `both` runs graph + vector + routing LLM call.
- **Pure semantic how-to** with no structural need — call `query_db.py` directly (one hop).
- **Keyflo product messaging / positioning** — use the separate Qdrant source-of-truth skill (`keyflo_source_of_truth` collection), not the learning corpus.

---

## References

| Doc | Location |
|---|---|
| Agentic router runbook | `langchain-course/docs/runbooks/agentic-router.md` |
| KG↔vector routing pattern | `langchain-course/patterns/proven/kg-vector-routing.md` |
| KB organization (layers, indexes) | `langchain-course/KB-ORGANIZATION.md` |
| Copy intake query map | `keyflo-marketing/pipeline/COPY-INTAKE-AND-GATES.md` §1 |
