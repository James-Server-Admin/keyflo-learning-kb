"""Read-only FastAPI gateway for the learning corpus agentic router."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from api.auth import require_api_key
from api.config import (
    LANGCHAIN_COURSE_REPO,
    MAX_K,
    MAX_QUESTION_LEN,
    RATE_LIMIT_PER_HOUR,
    load_api_keys,
)
from api.rate_limit import check_rate_limit


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=4000)
    k: int = Field(default=6, ge=1, le=12)
    max_retries: int = Field(default=2, ge=0, le=3)


class QueryResponse(BaseModel):
    answer: str
    route: str | None = None
    route_reason: str | None = None
    graph_context: str | None = None
    source_documents: list[str] = Field(default_factory=list)
    retries: int = 0


def _ensure_router_env() -> None:
    repo = LANGCHAIN_COURSE_REPO
    if not repo.is_dir():
        raise RuntimeError(f"langchain-course not found at {repo}")
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    import bootstrap

    bootstrap.load_env()


def _route_query(question: str, k: int, max_retries: int) -> dict[str, Any]:
    _ensure_router_env()
    from runtime.agentic_router import route_query

    capped_k = min(k, MAX_K)
    return route_query(question, k=capped_k, max_retries=max_retries)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    keys = load_api_keys()
    if not keys:
        raise RuntimeError(
            "No API keys configured — set LEARNING_KB_API_KEYS_PATH or LEARNING_KB_API_KEYS"
        )
    yield


app = FastAPI(
    title="Keyflo Learning KB API",
    description="Read-only query gateway to the learning corpus (Pinecone + Neo4j router).",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "learning-kb-api"}


@app.post("/v1/query", response_model=QueryResponse)
def query_corpus(
    body: QueryRequest,
    api_key: str = Depends(require_api_key),
) -> QueryResponse:
    check_rate_limit(api_key, limit_per_hour=RATE_LIMIT_PER_HOUR)
    question = body.question.strip()
    if len(question) > MAX_QUESTION_LEN:
        raise HTTPException(status_code=400, detail="question too long")
    try:
        result = _route_query(question, body.k, body.max_retries)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"router error: {type(exc).__name__}") from exc
    return QueryResponse(
        answer=result.get("answer") or "",
        route=result.get("route"),
        route_reason=result.get("route_reason"),
        graph_context=result.get("graph_context"),
        source_documents=list(result.get("source_documents") or []),
        retries=int(result.get("retries") or 0),
    )
