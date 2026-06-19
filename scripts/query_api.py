#!/usr/bin/env python3
"""Query the learning KB via the public HTTP API (no SSH required).

Usage:
    export LEARNING_KB_API_TOKEN="<from James>"
    python scripts/query_api.py "which courses cover copywriting?"
    python scripts/query_api.py --k 8 --json "how do I write PAS headlines?"

Optional env (see config/cole.env.example):
    LEARNING_KB_API_URL   default https://kb-api.keyflo.ai
    LEARNING_KB_API_TOKEN required
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://kb-api.keyflo.ai"


def main() -> int:
    p = argparse.ArgumentParser(description="Query learning KB over HTTPS")
    p.add_argument("question", help="natural language question")
    p.add_argument("--k", type=int, default=6, help="retrieval top-k (1-12, default 6)")
    p.add_argument("--max-retries", type=int, default=2, help="router retries (default 2)")
    p.add_argument("--json", action="store_true", help="print full JSON response")
    p.add_argument("--url", default=os.environ.get("LEARNING_KB_API_URL", DEFAULT_URL))
    args = p.parse_args()

    token = os.environ.get("LEARNING_KB_API_TOKEN", "").strip()
    if not token:
        print(
            "error: set LEARNING_KB_API_TOKEN (ask James for a bearer token)\n"
            "  export LEARNING_KB_API_TOKEN=...\n"
            "  or: source config/cole.env",
            file=sys.stderr,
        )
        return 1

    payload = json.dumps(
        {"question": args.question, "k": args.k, "max_retries": args.max_retries}
    ).encode()
    req = urllib.request.Request(
        f"{args.url.rstrip('/')}/v1/query",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"error: HTTP {exc.code} — {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"error: request failed — {exc.reason}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    route = data.get("route") or "?"
    print(f"ROUTE: {route}")
    if data.get("route_reason"):
        print(f"REASON: {data['route_reason']}")
    if data.get("graph_context"):
        print(f"\nGRAPH CONTEXT:\n{data['graph_context']}")
    print(f"\nANSWER:\n{data.get('answer', '')}")
    sources = data.get("source_documents") or []
    if sources:
        print("\nSOURCES:")
        for src in sources:
            print(f"  - {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
