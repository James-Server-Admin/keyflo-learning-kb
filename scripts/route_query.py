#!/usr/bin/env python3
"""Launch the agentic graph↔vector router (server-only).

Delegates to langchain-course runtime where full deps (LangGraph, Pinecone,
Neo4j, rigorous_benchmark, etc.) are installed.

Usage:
    source /mnt/blockstorage/env/load.sh
    python scripts/route_query.py "your question"
    python scripts/route_query.py --k 8 "your question"

Env:
    LANGCHAIN_COURSE_REPO  — path to langchain-course checkout (default /root/langchain-course)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Agentic router — auto-pick Pinecone vs Neo4j")
    p.add_argument("question", help="natural language question")
    p.add_argument("--k", type=int, default=6, help="retrieval top-k (default 6)")
    args = p.parse_args()

    repo = Path(os.environ.get("LANGCHAIN_COURSE_REPO", "/root/langchain-course"))
    runner = repo / "run"
    script = repo / "runtime" / "agentic_router.py"

    if not runner.is_file():
        print(
            f"error: langchain-course runner not found at {runner}\n"
            "Clone okrealai/langchain-course on the server or set LANGCHAIN_COURSE_REPO.",
            file=sys.stderr,
        )
        return 1

    if not script.is_file():
        print(
            f"error: agentic router not found at {script}\n"
            "Clone okrealai/langchain-course on the server or set LANGCHAIN_COURSE_REPO.",
            file=sys.stderr,
        )
        return 1

    cmd = [str(runner), str(script), args.question, "--k", str(args.k)]
    return subprocess.call(cmd, cwd=repo)


if __name__ == "__main__":
    sys.exit(main())
