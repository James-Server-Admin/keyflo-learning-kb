"""Configuration for the learning KB HTTP API (env-only — no secrets in repo)."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_KEYS_PATH = Path("/mnt/blockstorage/private/credentials/learning-kb-api-keys.txt")
DEFAULT_LANGCHAIN_REPO = Path("/root/langchain-course")


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def load_api_keys() -> frozenset[str]:
    """Bearer tokens allowed to call /v1/query (never log these)."""
    keys: set[str] = set()
    inline = os.environ.get("LEARNING_KB_API_KEYS", "")
    for part in inline.split(","):
        token = part.strip()
        if token:
            keys.add(token)

    path = Path(os.environ.get("LEARNING_KB_API_KEYS_PATH", str(DEFAULT_KEYS_PATH)))
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            keys.add(line)

    return frozenset(keys)


HOST = os.environ.get("LEARNING_KB_API_HOST", "127.0.0.1")
PORT = _int("LEARNING_KB_API_PORT", 8791)
MAX_K = _int("LEARNING_KB_API_MAX_K", 12)
MAX_QUESTION_LEN = _int("LEARNING_KB_API_MAX_QUESTION_LEN", 4000)
RATE_LIMIT_PER_HOUR = _int("LEARNING_KB_API_RATE_LIMIT_PER_HOUR", 30)
LANGCHAIN_COURSE_REPO = Path(os.environ.get("LANGCHAIN_COURSE_REPO", str(DEFAULT_LANGCHAIN_REPO)))
