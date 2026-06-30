#!/usr/bin/env python3
"""Read-only query CLI for the `learning` Pinecone index.

Embeds a question with OpenAI text-embedding-3-large (the index's embedding model —
do not change it; a different model's vectors are not comparable) and runs a
similarity search. Contains NO write operations by construction; pair with a
read-only Pinecone API key so writes are also impossible server-side.

Usage:
    source /mnt/blockstorage/env/load.sh   # server operator env
    # or export LEARNING_PINECONE_API_KEY + OPENAI_API_KEY (read-only keys from James)
    python scripts/query_db.py "your question"
    python scripts/query_db.py --namespace course-transcripts --k 8 "your question"
"""

import argparse
import sys

from env_loader import ensure_learning_pinecone_key, load_global_env, require_keys

INDEX = "learning"
EMBED_MODEL = "text-embedding-3-large"  # index contract: 3072d, immutable
ALLOWED_NAMESPACES = ["patterns", "course-transcripts", "langchain-docs", "research-papers"]


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only query against the learning index")
    p.add_argument("question")
    p.add_argument("--namespace", default="patterns", choices=ALLOWED_NAMESPACES,
                   help="namespace to search (in-scope namespaces only)")
    p.add_argument("--k", type=int, default=5, help="number of results")
    args = p.parse_args()

    try:
        load_global_env()
        ensure_learning_pinecone_key()
        require_keys("OPENAI_API_KEY")
    except RuntimeError as exc:
        print(f"error: {exc} (see docs/pinecone.md)", file=sys.stderr)
        return 1

    import os
    from openai import OpenAI
    from pinecone import Pinecone

    vector = OpenAI().embeddings.create(model=EMBED_MODEL, input=args.question).data[0].embedding

    index = Pinecone(api_key=os.environ["PINECONE_API_KEY"]).Index(INDEX)
    res = index.query(namespace=args.namespace, vector=vector, top_k=args.k,
                      include_metadata=True)

    matches = res.get("matches") or []
    if not matches:
        print(f"no results in namespace '{args.namespace}'")
        return 0

    for i, m in enumerate(matches, 1):
        meta = m.get("metadata") or {}
        source = meta.get("source", "(no source recorded)")
        text = (meta.get("text") or "").strip().replace("\n", " ")
        if len(text) > 400:
            text = text[:400] + " …"
        print(f"\n[{i}] score={m['score']:.3f}  source: {source}")
        print(f"    {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
