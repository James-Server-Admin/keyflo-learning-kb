#!/usr/bin/env bash
# Publish or refresh knowledge-base on GitHub (dual-hosted) + Cole runtime secrets.
# Requires: gh auth as admin on KeyFlo-ai and James-Server-Admin repos.
set -euo pipefail

ORG_REPO="KeyFlo-ai/knowledge-base"
EXTERNAL_REPO="James-Server-Admin/keyflo-learning-kb"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYNC_GH="/mnt/blockstorage/private/credentials/scripts/sync-knowledge-base-gh-secrets.sh"
MODE="${1:-all}"

cd "$ROOT"

sync_secrets() {
  if [[ ! -x "$SYNC_GH" ]]; then
    echo "error: missing $SYNC_GH" >&2
    exit 1
  fi
  "$SYNC_GH"
}

push_both() {
  git remote set-url origin "git@github.com:${ORG_REPO}.git"
  git push -u origin main
  if git remote get-url external &>/dev/null; then
    git push external main
  else
    git remote add external "git@github.com:${EXTERNAL_REPO}.git"
    git push -u external main
  fi
  echo "==> Pushed to ${ORG_REPO} and ${EXTERNAL_REPO}"
}

case "$MODE" in
  --secrets-only|secrets-only)
    sync_secrets
    ;;
  all|"")
    if gh repo view "$ORG_REPO" &>/dev/null; then
      echo "==> Org repo exists; pushing main to both remotes..."
      push_both
    else
      echo "==> Creating ${ORG_REPO} (private)..."
      gh repo create "$ORG_REPO" --private \
        --description "Learning corpus access (Pinecone + Neo4j) and agentic router docs" \
        --source=. --remote=origin --push
      if gh repo view "$EXTERNAL_REPO" &>/dev/null; then
        git remote add external "git@github.com:${EXTERNAL_REPO}.git" 2>/dev/null || true
        git push external main || echo "warn: external push failed (add remote manually)"
      fi
    fi
    sync_secrets
    echo "==> Done. Org: git@github.com:${ORG_REPO}.git"
    echo "==> External mirror: git@github.com:${EXTERNAL_REPO}.git (keep for outside-KeyFlo access)"
    ;;
  *)
    echo "Usage: $0 [all|--secrets-only]" >&2
    exit 1
    ;;
esac
