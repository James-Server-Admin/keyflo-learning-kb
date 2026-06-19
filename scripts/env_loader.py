"""Operator env helpers for keyflo-learning-kb CLIs.

Maps project-scoped LEARNING_* keys to SDK-expected names. Refuses the legacy
global PINECONE_API_KEY when LEARNING_PINECONE_API_KEY is absent — that key
points at a different Pinecone project and returns 404 on index `learning`.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_GLOBAL_ENV = Path("/mnt/blockstorage/env/global.env")


def load_global_env(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from global.env if the file exists."""
    env_path = path or Path(os.environ.get("KEYFLO_GLOBAL_ENV", str(DEFAULT_GLOBAL_ENV)))
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def ensure_learning_pinecone_key() -> None:
    learning = os.environ.get("LEARNING_PINECONE_API_KEY")
    if not learning:
        raise RuntimeError(
            "LEARNING_PINECONE_API_KEY not set — required for index `learning`. "
            "Ask the operator for read-only keys or run: source /mnt/blockstorage/env/load.sh global"
        )
    os.environ["PINECONE_API_KEY"] = learning


def require_keys(*names: str) -> None:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise RuntimeError(f"missing required env var(s): {', '.join(missing)}")
