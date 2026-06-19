"""Agentic RAG router — route between the knowledge graph and the vector store, grade, self-correct.

Corpus-grounded at every step (RUN-LOG Session 11 consults):
  • Architecture (udemy-langchain §10/066): agentic RAG = agent decides when/how to retrieve, ROUTES
    graph↔vector, GRADES context, SELF-CORRECTS → a LangGraph state machine.
  • Routing (advanced-langchain): LOGICAL routing = an LLM structured-output classifier picks the
    data source (graph | vector | both).
  • Division of labour (kg-vector-routing.md + rigorous_benchmark, proven): GRAPH for coverage /
    disputes / structure / multi-hop; VECTOR for semantic / fine-grained; BOTH for combined.
  • Grade + retry (graph_query.py + lib.retrieval_grader): corrective-RAG retrieve→grade→widen-k.
  • Fusion (corpus §14/077): the `both` route RRF-fuses the vector + graph source rankings via the
    benchmark's `_rrf` (the cross-category-winning 'both' arm); structural graph facts are prepended
    separately. The `vector` route keeps the A/B-proven cross-encoder rerank (no rank fusion).
Traced as `agentic_router` in LangSmith LANGCHAIN-APP. Reuses runtime.query (vector text + grader +
RAGResponse) and the benchmark primitives (topic centroids, graph sources, RRF).

  ./run runtime/agentic_router.py "do any courses disagree about how to open a negotiation?"
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "eval" / "graph")); sys.path.insert(0, str(REPO / "graph"))

import bootstrap
bootstrap.load_env()

from langgraph.graph import END, START, StateGraph
from langsmith import traceable
from pydantic import BaseModel, Field

import config
from lib.models import get_chat_model
from lib.structured_responses import RAGResponse
from runtime.query import _get_retriever, _rerank, _get_namespace_prompt, format_docs_with_sources, _source_ids
import eval.graph.rigorous_benchmark as bench  # _embed, _nearest_topic, _vector_sources, _graph_sources, _rrf, ex
from ingest.ingest_files import file_slug

NS = "course-transcripts"


# ───────────────────────── retrieval helpers ─────────────────────────
def _vector_docs(question, k, rerank=True):
    r = _get_retriever(NS, k=k * 3 if rerank else k)
    docs = r.invoke(question)
    return _rerank(question, docs, top_k=k) if rerank else docs


def _text_for_source(src, qv, n=2):
    """K1 drill-down: lecture source → vector_id_prefix → its top-n chunks' text (graph→vector bridge)."""
    idx = bench.ex._pine()
    ids = [b for batch in idx.list(namespace=NS, prefix=file_slug(Path(src)) + "#") for b in batch][:n]
    if not ids:
        return ""
    fetched = idx.fetch(ids=ids, namespace=NS).vectors or {}
    return "\n".join((v.metadata or {}).get("text", "") for v in fetched.values())[:1200]


def _nearest_topics(qv, n=5) -> list[str]:
    """Top-n nearest topic keys by centroid similarity (disputes live on only ~6 of 454 topics, so
    top-1 rarely lands on a disputed one — scan a small neighbourhood instead)."""
    import numpy as np
    st = bench._structures()
    ts = list(st["centroids"])
    C = np.vstack([st["centroids"][t] for t in ts])
    order = (C @ qv).argsort()[::-1][:n]
    return [ts[int(i)] for i in order]


def _graph_facts(qv) -> str:
    """The graph's UNIQUE value: nearest topic → which courses cover it (multi-hop, top-1) + any
    disputes (CQ3) across the nearest neighbourhood. Claim text lives in `statement` (not `text`)."""
    topics = _nearest_topics(qv, n=5)
    facts = []
    try:
        with bench.ex._driver().session() as s:
            r = s.run("MATCH (l:Lecture)-[:COVERS]->(t:Topic {key:$k}) "
                      "RETURN t.label AS label, count(DISTINCT l.course) AS nc, "
                      "collect(DISTINCT l.course)[..5] AS courses", k=topics[0]).single()
            if r:
                facts.append(f"Topic '{r['label']}' is covered across {r['nc']} course(s): {', '.join(r['courses'])}.")
            seen = set()
            for tk in topics:
                d = s.run("MATCH (c:Claim {topic_key:$k})-[:CONTRADICTS]->(c2:Claim) "
                          "RETURN c.statement AS a, c.course AS ac, c2.statement AS b, c2.course AS bc, "
                          "c.aspect AS aspect LIMIT 3", k=tk).data()
                for row in d:
                    sig = (str(row['a'])[:40], str(row['b'])[:40])
                    if sig in seen:
                        continue
                    seen.add(sig)
                    facts.append(f"DISPUTE ({row.get('aspect') or 'claim'}): {row['ac']} says "
                                 f"\"{str(row['a'])[:110]}\" — but {row['bc']} says \"{str(row['b'])[:110]}\".")
    except Exception as e:
        facts.append(f"(graph facts unavailable: {type(e).__name__})")
    return "\n".join(facts)


# ───────────────────────── state + nodes ─────────────────────────
class S(TypedDict, total=False):
    question: str
    k: int
    retry_count: int
    max_retries: int
    route: str
    route_reason: str
    docs: list
    graded: list
    graph_context: str
    response: dict


class Route(BaseModel):
    """Logical routing decision (LLM structured output)."""
    route: Literal["vector", "graph", "both"] = Field(description=
        "graph = coverage/gap, disagreement/dispute, or structural/multi-hop questions; "
        "vector = specific/semantic/how-to/factual passage questions; both = broad questions wanting "
        "a synthesized answer plus structural context")
    reason: str


@traceable(name="route_node", run_type="chain")
def node_route(state: S) -> S:
    r = get_chat_model("grader", temperature=0.0).with_structured_output(Route).invoke(
        "Classify this question to pick the retrieval source.\n"
        "- graph: COVERAGE ('what does the corpus cover/not cover'), DISPUTES ('do sources disagree on X'), "
        "STRUCTURE/multi-hop ('which courses cover X', 'how do topics relate')\n"
        "- vector: specific/how-to/factual ('how do I X', 'what is X', 'explain X')\n"
        "- both: broad synthesis questions wanting an answer + structural context\n\n"
        f"Question: {state['question']}")
    return {**state, "route": r.route, "route_reason": r.reason}


def _docs_from_sources(srcs, qv):
    from langchain_core.documents import Document
    docs = (Document(page_content=_text_for_source(s, qv), metadata={"source": s}) for s in srcs)
    return [d for d in docs if d.page_content]


@traceable(name="retrieve_node", run_type="chain")
def node_retrieve(state: S) -> S:
    q, k, route = state["question"], state.get("k", 6), state["route"]
    qv = bench.ex._embed(q)
    docs, gctx = [], ""
    if route == "vector":  # pure semantic — retriever + A/B-proven cross-encoder rerank
        docs = _vector_docs(q, k)
    elif route == "graph":  # structural facts + topic-scoped lecture text as passages
        gctx = _graph_facts(qv)
        docs = _docs_from_sources(bench._graph_sources(qv, k), qv)
    else:  # both — RRF-fuse the vector + graph source rankings (corpus §14/077; the benchmark's
           # cross-category-winning 'both' arm) AND prepend the graph's structural facts
        gctx = _graph_facts(qv)
        fused = bench._rrf([bench._vector_sources(qv, k * 2), bench._graph_sources(qv, k * 2)], k)
        docs = _docs_from_sources(fused, qv)
    return {**state, "docs": docs, "graph_context": gctx}


@traceable(name="grade_node", run_type="chain")
def node_grade(state: S) -> S:
    from lib.retrieval_grader import grade_docs
    docs = state.get("docs") or []
    keep = [d for d, sc in grade_docs(state["question"], docs) if sc == "yes"] if docs else []
    return {**state, "graded": keep}


def cond_after_grade(state: S) -> str:
    if state.get("graded") or state.get("graph_context"):
        return "answer"
    if state.get("retry_count", 0) >= state.get("max_retries", 2):
        return "answer"  # answer-with-graph-facts or honest refusal happens in node_answer
    return "widen"


def node_widen(state: S) -> S:
    return {**state, "k": state.get("k", 6) * 2, "retry_count": state.get("retry_count", 0) + 1}


@traceable(name="answer_node", run_type="chain")
def node_answer(state: S) -> S:
    docs = state.get("graded") or state.get("docs") or []
    ctx = format_docs_with_sources(docs) if docs else ""
    gctx = state.get("graph_context") or ""
    full = (f"[GRAPH CONTEXT]\n{gctx}\n\n" if gctx else "") + (f"[RETRIEVED PASSAGES]\n{ctx}" if ctx else "")
    if not full.strip():
        return {**state, "response": RAGResponse(answer="No relevant context found.", confidence=0.0,
                                                 top_source=None, sources=[], refused=True,
                                                 refusal_reason="router: no graph facts and grader kept 0 chunks").model_dump()}
    tmpl = _get_namespace_prompt(NS)
    formatted = tmpl.invoke({"context": full, "question": state["question"]})
    resp = get_chat_model("answer").with_structured_output(RAGResponse).invoke(formatted)
    return {**state, "response": resp.model_dump()}


def _build():
    g = StateGraph(S)
    for name, fn in [("route", node_route), ("retrieve", node_retrieve), ("grade", node_grade),
                     ("widen", node_widen), ("answer", node_answer)]:
        g.add_node(name, fn)
    g.add_edge(START, "route")
    g.add_edge("route", "retrieve")
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", cond_after_grade, {"answer": "answer", "widen": "widen"})
    g.add_edge("widen", "retrieve")
    g.add_edge("answer", END)
    return g.compile()


_GRAPH = None


@traceable(name="agentic_router", run_type="chain")
def route_query(question: str, k: int = 6, max_retries: int = 2) -> dict:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build()
    final = _GRAPH.invoke({"question": question, "k": k, "max_retries": max_retries,
                           "retry_count": 0})
    docs = final.get("graded") or final.get("docs") or []
    return {
        "answer": final["response"]["answer"],
        "route": final.get("route"), "route_reason": final.get("route_reason"),
        "graph_context": final.get("graph_context"),
        "source_documents": _source_ids(docs),
        "structured_response": final["response"],
        "retries": final.get("retry_count", 0),
    }


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", default="do any courses disagree about how to open a negotiation?")
    ap.add_argument("--k", type=int, default=6)
    args = ap.parse_args()
    out = route_query(args.question, k=args.k)
    print(f"ROUTE: {out['route']}  ({out['route_reason']})\n")
    if out["graph_context"]:
        print(f"GRAPH CONTEXT:\n{out['graph_context']}\n")
    print(f"ANSWER:\n{out['answer']}\n")
    print(f"sources: {[s.split('/')[-1] for s in (out['source_documents'] or [])][:5]} | retries: {out['retries']}")
