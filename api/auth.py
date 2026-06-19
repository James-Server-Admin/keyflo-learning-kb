"""Bearer token authentication for the learning KB API."""

from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import load_api_keys

_bearer = HTTPBearer(auto_error=False)
_allowed: frozenset[str] | None = None


def _allowed_keys() -> frozenset[str]:
    global _allowed
    if _allowed is None:
        _allowed = load_api_keys()
    return _allowed


def reload_keys() -> None:
    global _allowed
    _allowed = None


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="missing or invalid Authorization header")
    token = credentials.credentials.strip()
    if not token or token not in _allowed_keys():
        raise HTTPException(status_code=401, detail="invalid api key")
    return token
