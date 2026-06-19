#!/usr/bin/env bash
# One-time operator step: move this repo into the KeyFlo-ai org.
# Requires gh auth as an org admin (James / okrealai), not agent-smithj.
set -euo pipefail

SRC="${1:-James-Server-Admin/keyflo-learning-kb}"
DST="KeyFlo-ai/keyflo-learning-kb"

echo "Creating ${DST} and pushing from local checkout..."
gh repo create "$DST" --private --description "Read-only learning corpus access (Pinecone + Neo4j) and agentic router docs"
git remote set-url origin "git@github.com:${DST}.git"
git push -u origin main

echo "Archive interim repo ${SRC} (optional):"
echo "  gh repo delete ${SRC} --yes"
