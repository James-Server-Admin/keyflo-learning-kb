#!/usr/bin/env bash
# Publish or refresh KeyFlo-ai/knowledge-base GitHub repo + Cole runtime secrets.
# Requires: gh auth as KeyFlo-ai org admin (James / okrealai), not agent-smithj.
set -euo pipefail

REPO="KeyFlo-ai/knowledge-base"
INTERIM="James-Server-Admin/keyflo-learning-kb"
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

case "$MODE" in
  --secrets-only|secrets-only)
    sync_secrets
    ;;
  all|"")
    if gh repo view "$REPO" &>/dev/null; then
      echo "==> Repo exists; pushing main..."
      git remote set-url origin "git@github.com:${REPO}.git"
      git push -u origin main
    else
      echo "==> Creating ${REPO} (private) and pushing main..."
      gh repo create "$REPO" --private \
        --description "Learning corpus access (Pinecone + Neo4j) and agentic router docs" \
        --source=. --remote=origin --push
    fi
    sync_secrets
    echo "==> Done. Canonical remote: git@github.com:${REPO}.git"
    if gh repo view "$INTERIM" &>/dev/null; then
      echo "==> Optional: delete interim repo: gh repo delete ${INTERIM} --yes"
    fi
    ;;
  *)
    echo "Usage: $0 [all|--secrets-only]" >&2
    exit 1
    ;;
esac
