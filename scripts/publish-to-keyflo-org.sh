#!/usr/bin/env bash
# Publish knowledge-base to KeyFlo-ai org (one-time operator step).
# Requires: gh auth as KeyFlo-ai org admin (James / okrealai), not agent-smithj.
set -euo pipefail

REPO="KeyFlo-ai/knowledge-base"
INTERIM="James-Server-Admin/keyflo-learning-kb"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYNC="/mnt/blockstorage/private/credentials/scripts/sync-gh-secret-from-env.sh"
GLOBAL="/mnt/blockstorage/env/global.env"

cd "$ROOT"

echo "==> Creating ${REPO} (private) and pushing main..."
gh repo create "$REPO" --private \
  --description "Learning corpus access (Pinecone + Neo4j) and agentic router docs" \
  --source=. --remote=origin --push

echo "==> Syncing GitHub Actions secrets from global.env..."
for key in LEARNING_PINECONE_API_KEY LEARNING_KG_NEO4J_URI LEARNING_KG_NEO4J_USER LEARNING_KG_NEO4J_PASSWORD OPENAI_API_KEY; do
  val="$(grep "^${key}=" "$GLOBAL" | cut -d= -f2-)"
  [[ -n "$val" ]] || { echo "skip empty: $key" >&2; continue; }
  printf '%s' "$val" | gh secret set "$key" -R "$REPO"
  echo "  ok secret: $key"
done
printf '%s' '/root/langchain-course' | gh secret set LANGCHAIN_COURSE_REPO -R "$REPO"

BUNDLE="$(mktemp)"
{
  echo "# LEARNING_KB_COLE_RUNTIME — dotenv for smoke-query workflow"
  echo "KEYFLO_SERVER_HOST=192.241.169.31"
  echo "KEYFLO_SERVER_SSH_USER=root"
  echo "LANGCHAIN_COURSE_REPO=/root/langchain-course"
  grep '^LEARNING_KG_NEO4J_URI=' "$GLOBAL"
  grep '^LEARNING_KG_NEO4J_USER=' "$GLOBAL"
  grep '^LEARNING_KG_NEO4J_PASSWORD=' "$GLOBAL"
  grep '^LEARNING_PINECONE_API_KEY=' "$GLOBAL"
  grep '^OPENAI_API_KEY=' "$GLOBAL"
} > "$BUNDLE"
gh secret set LEARNING_KB_COLE_RUNTIME -R "$REPO" < "$BUNDLE"
rm -f "$BUNDLE"

gh variable set LANGCHAIN_COURSE_REPO --body "/root/langchain-course" -R "$REPO"
gh variable set KEYFLO_SERVER_HOST --body "192.241.169.31" -R "$REPO"
gh variable set KEYFLO_SERVER_SSH_USER --body "root" -R "$REPO"
gh variable set LEARNING_KG_NEO4J_URI --body "bolt://localhost:7689" -R "$REPO"
gh variable set COLE_SETUP --body "Clone KeyFlo-ai/knowledge-base. SSH root@192.241.169.31 for Neo4j. Secrets: LEARNING_KB_COLE_RUNTIME. Actions: smoke-query (needs keyflo-server runner)." -R "$REPO"

echo "==> Done. Canonical remote: git@github.com:${REPO}.git"
if gh repo view "$INTERIM" &>/dev/null; then
  echo "==> Optional: delete interim repo: gh repo delete ${INTERIM} --yes"
fi
