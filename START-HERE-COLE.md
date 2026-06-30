# START HERE — Cole

**This folder is ready to use.** No clone, no `gh auth`, no setup scripts.

## For your AI

Tell your coding agent:

> Read `AGENTS.md` in this folder. It explains how to query James's learning corpus across courses, patterns, and research papers. Credentials are already in `config/cole.env`. To run a broad query: `source config/cole.env && python3 scripts/query_api.py "your question"`. Read-only access only.

**Primary instruction file:** [`AGENTS.md`](AGENTS.md)

## Quick test (you)

```bash
cd /path/to/this/folder
source config/cole.env
python3 scripts/query_api.py "which courses cover copywriting?"
```

## What's in here

| Path | Purpose |
|------|---------|
| `AGENTS.md` | **Give this to your AI** — routing rules, tools, boundaries |
| `config/cole.env` | Pre-configured API access (do not share or commit) |
| `scripts/query_api.py` | Query the corpus over HTTPS |
| `docs/` | Routing, Pinecone, Neo4j, API reference |
| `docs/COLE-SETUP.md` | Full reference (optional) |

## API

- Health: `https://kb-api.keyflo.ai/health`
- Queries: `scripts/query_api.py` (uses token in `config/cole.env`)

## Rules

- **Read only** — never write to Pinecone or Neo4j
- **Do not** commit or upload `config/cole.env`
- This corpus is James's learning library — not Keyflo product messaging (see AGENTS.md for what *not* to use this for)

## GitHub (optional)

Same content lives at `KeyFlo-ai/knowledge-base` if you prefer git pull updates later. This Drive copy is the zero-setup snapshot from James.
