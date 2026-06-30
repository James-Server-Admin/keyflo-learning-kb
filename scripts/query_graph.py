#!/usr/bin/env python3
"""Read-only Neo4j query CLI for the learning knowledge graph.

Wraps the same marketing-scoped read-only queries used by the pipeline
(kg_queries.py). No write operations by construction.

Usage:
    export LEARNING_KG_NEO4J_URI=bolt://...
    export LEARNING_KG_NEO4J_USER=neo4j
    export LEARNING_KG_NEO4J_PASSWORD=...

    python query_graph.py --stats
    python query_graph.py --lane copy
    python query_graph.py --topics "headline persuasion"
    python query_graph.py --topics "langsmith tracing"   # multi-surface (topic+narrow+discipline+lecture)
    python query_graph.py --disputes
"""

from __future__ import annotations

import argparse
import os
import re
import sys

LANE_KEYWORDS: dict[str, list[str]] = {
    "copy": ["copy", "headline", "storytelling", "persuasion", "email", "writing"],
    "design": ["design", "creative", "image", "visual", "scroll", "contrast", "canva", "photoshop"],
    "campaign": ["campaign", "ad set", "budget", "audience", "targeting", "objective", "facebook"],
    "tracking": ["conversion", "tracking", "pixel", "remarketing", "attribution", "landing page"],
}

WRITE_PATTERN = re.compile(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b", re.I)

# Surfaces searched by --topics (W23 — lexical label gap fix)
TOPIC_SURFACES = ("topic", "narrow", "discipline", "lecture")


def _require_env() -> tuple[str, str, str]:
    from env_loader import load_global_env

    load_global_env()
    missing = [v for v in ("LEARNING_KG_NEO4J_URI", "LEARNING_KG_NEO4J_USER", "LEARNING_KG_NEO4J_PASSWORD")
               if not os.environ.get(v)]
    if missing:
        print(f"error: missing env var(s): {', '.join(missing)} (see docs/neo4j.md)", file=sys.stderr)
        sys.exit(1)
    return (
        os.environ["LEARNING_KG_NEO4J_URI"],
        os.environ["LEARNING_KG_NEO4J_USER"],
        os.environ["LEARNING_KG_NEO4J_PASSWORD"],
    )


def _assert_read_only(cypher: str) -> None:
    if WRITE_PATTERN.search(cypher):
        print("error: read-only CLI — write keywords not allowed", file=sys.stderr)
        sys.exit(1)


def _run(cypher: str, **params) -> list[dict]:
    _assert_read_only(cypher)
    from neo4j import GraphDatabase, READ_ACCESS

    uri, user, password = _require_env()
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session(default_access_mode=READ_ACCESS) as session:
            return [r.data() for r in session.run(cypher, **params)]


def cmd_stats() -> None:
    rows = _run("""
CALL () { MATCH (c:Course) RETURN count(c) AS courses }
CALL () { MATCH (l:Lecture) RETURN count(l) AS lectures }
CALL () { MATCH (t:Topic) WHERE NOT t:Admin RETURN count(t) AS topics }
CALL () { MATCH (d:Discipline) RETURN count(d) AS disciplines }
CALL () { MATCH (cl:Claim) RETURN count(cl) AS claims }
RETURN courses, lectures, topics, disciplines, claims
    """.strip())
    if not rows:
        print("no stats returned")
        return
    s = rows[0]
    print("Learning KG stats:")
    for k in ("courses", "lectures", "topics", "disciplines", "claims"):
        print(f"  {k}: {s.get(k, '?')}")


def _search_topics(keywords: list[str], limit: int) -> list[dict]:
    return _run("""
MATCH (l:Lecture)-[:COVERS]->(t:Topic)
WHERE NOT t:Admin AND any(kw IN $kws WHERE toLower(t.label) CONTAINS kw)
RETURN t.label AS label, t.domain AS domain,
       count(DISTINCT l) AS lectures, count(DISTINCT l.course) AS courses
ORDER BY lectures DESC LIMIT $limit
    """.strip(), kws=keywords, limit=limit)


def _search_narrow(keywords: list[str], limit: int) -> list[dict]:
    return _run("""
MATCH (n:Narrow)
WHERE any(kw IN $kws WHERE toLower(n.name) CONTAINS kw)
RETURN n.name AS label, n.broader AS domain,
       coalesce(n.lectures_assigned, 0) AS lectures, null AS courses
ORDER BY lectures DESC LIMIT $limit
    """.strip(), kws=keywords, limit=limit)


def _search_disciplines(keywords: list[str], limit: int) -> list[dict]:
    return _run("""
MATCH (d:Discipline)
WHERE NOT d:Narrow AND any(kw IN $kws WHERE toLower(d.name) CONTAINS kw)
RETURN d.name AS label, d.domain AS domain,
       null AS lectures, null AS courses
ORDER BY d.name LIMIT $limit
    """.strip(), kws=keywords, limit=limit)


def _search_lecture_titles(keywords: list[str], limit: int) -> list[dict]:
    return _run("""
MATCH (l:Lecture)
WITH l, [kw IN $kws WHERE toLower(l.title) CONTAINS kw] AS matched
WHERE size(matched) > 0
RETURN l.course AS course, l.title AS label,
       size(matched) AS kw_matches,
       reduce(score = 0, kw IN matched | score + size(kw)) AS kw_score
ORDER BY kw_score DESC, kw_matches DESC, l.course, l.title LIMIT $limit
    """.strip(), kws=keywords, limit=limit)


def _print_surface(surface: str, rows: list[dict], start_index: int) -> int:
    idx = start_index
    for r in rows:
        label = r.get("label") or "?"
        if surface == "lecture":
            course = r.get("course") or "?"
            print(f"\n[{idx}] surface=lecture  {course}")
            print(f"    {label}")
        else:
            domain = r.get("domain")
            lectures = r.get("lectures")
            courses = r.get("courses")
            domain_bit = f"  ({domain})" if domain else ""
            print(f"\n[{idx}] surface={surface}  {label}{domain_bit}")
            if surface == "narrow":
                print(f"    {lectures} lectures assigned (ontology)")
            elif courses is not None:
                print(f"    {lectures} lectures across {courses} course(s)")
            elif lectures:
                print(f"    {lectures} lecture(s)")
            else:
                print(f"    (reference frame)")
        idx += 1
    return idx


def cmd_topics(keywords: list[str], limit: int = 12) -> None:
    """Multi-surface keyword search — Topic.label alone misses product-specific terms."""
    per_surface = max(limit, 8)

    topic_rows = _search_topics(keywords, per_surface)
    narrow_rows = _search_narrow(keywords, per_surface)
    discipline_rows = _search_disciplines(keywords, per_surface)
    lecture_rows = _search_lecture_titles(keywords, per_surface)

    total = len(topic_rows) + len(narrow_rows) + len(discipline_rows) + len(lecture_rows)
    if total == 0:
        print(f"no matches on any surface for keywords: {keywords}")
        print(f"  surfaces searched: {', '.join(TOPIC_SURFACES)}")
        return

    print(f"keywords: {keywords}")
    print(f"surfaces: {', '.join(TOPIC_SURFACES)}  (matches: topic={len(topic_rows)}, "
          f"narrow={len(narrow_rows)}, discipline={len(discipline_rows)}, lecture={len(lecture_rows)})")

    idx = 1
    if topic_rows:
        print("\n--- Topic (cluster labels) ---")
        idx = _print_surface("topic", topic_rows, idx)
    if narrow_rows:
        print("\n--- Narrow (external ontology sub-skills) ---")
        idx = _print_surface("narrow", narrow_rows, idx)
    if discipline_rows:
        print("\n--- Discipline (reference frame) ---")
        idx = _print_surface("discipline", discipline_rows, idx)
    if lecture_rows:
        print("\n--- Lecture (title match) ---")
        _print_surface("lecture", lecture_rows, idx)


def cmd_disputes(min_conf: float = 0.6) -> None:
    rows = _run("""
MATCH (a:Claim)-[r:CONTRADICTS]->(b:Claim)
WHERE a.course <> b.course AND r.confidence >= $min_conf
  AND (a.domain IN ['marketing','sales'] OR b.domain IN ['marketing','sales'])
RETURN r.confidence AS confidence, a.course AS course_a, a.statement AS claim_a,
       b.course AS course_b, b.statement AS claim_b, r.explanation AS why
ORDER BY r.confidence DESC LIMIT 8
    """.strip(), min_conf=min_conf)
    if not rows:
        print("no marketing/sales disputes at or above confidence threshold")
        return
    for i, r in enumerate(rows, 1):
        ca = (r.get("claim_a") or "")[:120]
        cb = (r.get("claim_b") or "")[:120]
        print(f"\n[{i}] confidence={r.get('confidence', '?')}")
        print(f"    {r.get('course_a')}: \"{ca}…\"")
        print(f"    {r.get('course_b')}: \"{cb}…\"")
        if r.get("why"):
            print(f"    why: {str(r['why'])[:200]}")


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only Neo4j queries against learning-kg-neo4j")
    p.add_argument("--stats", action="store_true", help="corpus node counts")
    p.add_argument("--lane", choices=sorted(LANE_KEYWORDS), help="marketing lane topic search")
    p.add_argument("--topics", metavar="WORDS", help="space-separated keywords (multi-surface search)")
    p.add_argument("--disputes", action="store_true", help="cross-course marketing disputes")
    p.add_argument("--limit", type=int, default=12, help="max rows per surface (default 12)")
    args = p.parse_args()

    actions = sum([args.stats, bool(args.lane), bool(args.topics), args.disputes])
    if actions != 1:
        print("error: specify exactly one of --stats, --lane, --topics, --disputes", file=sys.stderr)
        return 1

    try:
        if args.stats:
            cmd_stats()
        elif args.lane:
            print(f"Lane: {args.lane}  keywords: {', '.join(LANE_KEYWORDS[args.lane])}")
            cmd_topics(LANE_KEYWORDS[args.lane], limit=args.limit)
        elif args.topics:
            kws = [w.lower() for w in args.topics.split() if len(w) >= 3]
            if not kws:
                print("error: --topics needs at least one keyword (3+ chars)", file=sys.stderr)
                return 1
            cmd_topics(kws, limit=args.limit)
        elif args.disputes:
            cmd_disputes()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
