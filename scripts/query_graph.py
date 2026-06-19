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
CALL { MATCH (c:Course) RETURN count(c) AS courses }
CALL { MATCH (l:Lecture) RETURN count(l) AS lectures }
CALL { MATCH (t:Topic) WHERE NOT t:Admin RETURN count(t) AS topics }
CALL { MATCH (d:Discipline) RETURN count(d) AS disciplines }
CALL { MATCH (cl:Claim) RETURN count(cl) AS claims }
RETURN courses, lectures, topics, disciplines, claims
    """.strip())
    if not rows:
        print("no stats returned")
        return
    s = rows[0]
    print("Learning KG stats:")
    for k in ("courses", "lectures", "topics", "disciplines", "claims"):
        print(f"  {k}: {s.get(k, '?')}")


def cmd_topics(keywords: list[str], limit: int = 12) -> None:
    rows = _run("""
MATCH (l:Lecture)-[:COVERS]->(t:Topic)
WHERE NOT t:Admin AND any(kw IN $kws WHERE toLower(t.label) CONTAINS kw)
RETURN t.domain AS domain, t.label AS topic,
       count(DISTINCT l) AS lectures, count(DISTINCT l.course) AS courses
ORDER BY lectures DESC LIMIT $limit
    """.strip(), kws=keywords, limit=limit)
    if not rows:
        print(f"no topics matched keywords: {keywords}")
        return
    for i, r in enumerate(rows, 1):
        print(f"\n[{i}] {r['topic']}  ({r['domain']})")
        print(f"    {r['lectures']} lectures across {r['courses']} course(s)")


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
    p.add_argument("--topics", metavar="WORDS", help="space-separated keywords for topic search")
    p.add_argument("--disputes", action="store_true", help="cross-course marketing disputes")
    p.add_argument("--limit", type=int, default=12, help="max topic rows (default 12)")
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
