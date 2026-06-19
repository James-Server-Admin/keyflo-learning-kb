# Cole setup — learning knowledge base

**Repo:** `KeyFlo-ai/knowledge-base` (you are here)  
**Purpose:** Query James's personal learning corpus (~116 marketing/engineering courses) via Pinecone + Neo4j, with an agentic router that picks the right store.

---

## MCP in Cursor (recommended)

Use the learning KB as an MCP server in Cursor — no SSH, same corpus:

| Item | Value |
|------|-------|
| **Setup repo** | [`KeyFlo-ai/kb-gateway`](https://github.com/KeyFlo-ai/kb-gateway) |
| **MCP URL** | `https://kb-mcp.waytie.com/mcp` |
| **GitHub variable** | `COLE_SETUP` on `KeyFlo-ai/kb-gateway` → [`docs/COLE-SETUP.md`](https://github.com/KeyFlo-ai/kb-gateway/blob/main/docs/COLE-SETUP.md) |

```bash
git clone git@github.com:KeyFlo-ai/kb-gateway.git
cd kb-gateway
gh auth login
./scripts/setup-mcp.sh
# paste config/mcp.json → Cursor Settings → MCP
```

Tools: `route_query`, `query_namespace`, `graph_query`, `list_namespaces`, `health`.

---

## Quick start — HTTP API (scripts / no MCP)

Everything below is the **HTTP API** path. Bearer token: GitHub variable `LEARNING_KB_API_TOKEN` on this repo — run `./scripts/setup-cole-env.sh` after `gh auth login`.

1. **Clone this repo**
   ```bash
   git clone git@github.com:KeyFlo-ai/knowledge-base.git
   cd knowledge-base
   gh auth login   # once, as your GitHub user with repo access
   ```

2. **Create local env from GitHub variable**
   ```bash
   chmod +x scripts/setup-cole-env.sh
   ./scripts/setup-cole-env.sh
   source config/cole.env
   ```

3. **Verify the API is up**
   ```bash
   curl -s https://kb-api.keyflo.ai/health
   # {"status":"ok","service":"learning-kb-api"}
   ```

4. **Run a query**
   ```bash
   python scripts/query_api.py "which courses cover copywriting?"
   ```

5. **Point your coding agent at** [`AGENTS.md`](../AGENTS.md) — routing rules, when to use vector vs graph, read-only boundaries.

**Manual fallback:** copy `LEARNING_KB_API_TOKEN` from repo **Settings → Secrets and variables → Actions → Variables** into `config/cole.env`.

---

## Access paths (pick one)

| Path | When | What you need |
|------|------|----------------|
| **HTTP API** (default) | Day-to-day Q&A from your laptop | Bearer token from James |
| **SSH + CLI** | Debugging graph/Cypher, bulk scripts | SSH key to `root@192.241.169.31` + env keys from James |
| **GitHub Actions** | Smoke tests on the server | Repo secrets already configured; self-hosted runner `keyflo-server` |

### HTTP API (default)

| Item | Value |
|------|-------|
| Base URL | `https://kb-api.keyflo.ai` |
| Health | `GET /health` (no auth) |
| Query | `POST /v1/query` (Bearer token) |
| Rate limit | 30 requests/hour per token |
| Docs | [`docs/public-api.md`](public-api.md) |

```bash
export LEARNING_KB_API_TOKEN="<from James>"
python scripts/query_api.py "how do I structure a Meta lead gen campaign?"
python scripts/query_api.py --k 8 "do any courses disagree about negotiation openings?"
python scripts/query_api.py --json "which courses cover StoryBrand?"
```

```bash
curl -s https://kb-api.keyflo.ai/v1/query \
  -H "Authorization: Bearer $LEARNING_KB_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"which courses cover copywriting?","k":6}'
```

**Python (for agents / apps):**

```python
import os, json, urllib.request

url = "https://kb-api.keyflo.ai/v1/query"
token = os.environ["LEARNING_KB_API_TOKEN"]
body = json.dumps({"question": "which courses cover copywriting?", "k": 6}).encode()
req = urllib.request.Request(
    url, data=body, method="POST",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=120) as resp:
    print(json.load(resp)["answer"])
```

### SSH + CLI (optional)

Neo4j is **server-local** (`bolt://localhost:7689`). For direct Pinecone/Neo4j CLIs or the full router without HTTP:

```bash
ssh root@192.241.169.31
git clone git@github.com:KeyFlo-ai/knowledge-base.git && cd knowledge-base
pip install -r requirements.txt
# James provides env keys or you use server load.sh if you have access:
source /mnt/blockstorage/env/load.sh
python scripts/route_query.py "which courses cover copywriting?"
python scripts/query_graph.py --disputes
python scripts/query_db.py --namespace course-transcripts "PAS headline formulas"
```

Router runtime also needs [`okrealai/langchain-course`](https://github.com/okrealai/langchain-course) at `/root/langchain-course` on the server (already there).

### GitHub Actions (optional)

Repo → **Actions** → **smoke-query** → Run workflow.

Requires a self-hosted runner labeled `keyflo-server` on this repo (same machine as Neo4j). Until that runner exists, use the HTTP API or SSH.

Secrets and variables are pre-synced by James — see table below.

---

## GitHub Settings (already configured)

**Settings → Secrets and variables → Actions**

| Name | Type | Purpose |
|------|------|---------|
| `COLE_SETUP` | Variable | Pointer to this file (HTTP API); MCP → `KeyFlo-ai/kb-gateway` |
| `KB_GATEWAY_MCP_URL` | Variable | `https://kb-mcp.waytie.com/mcp` |
| `KB_GATEWAY_MCP_TOKEN` | Variable | Same bearer as `LEARNING_KB_API_TOKEN` — for MCP |
| `KB_GATEWAY_REPO` | Variable | `KeyFlo-ai/kb-gateway` — clone for `./scripts/setup-mcp.sh` |
| `KEYFLO_SERVER_HOST` | Variable | `192.241.169.31` |
| `KEYFLO_SERVER_SSH_USER` | Variable | `root` |
| `LEARNING_KG_NEO4J_URI` | Variable | `bolt://localhost:7689` |
| `LEARNING_KB_API_URL` | Variable | `https://kb-api.keyflo.ai` |
| `LEARNING_KB_API_TOKEN` | Variable | Bearer token for `/v1/query` — use `./scripts/setup-cole-env.sh` |
| `LANGCHAIN_COURSE_REPO` | Variable | `/root/langchain-course` |
| `LEARNING_KB_COLE_RUNTIME` | Secret | Dotenv bundle for smoke-query workflow |
| `LEARNING_PINECONE_API_KEY` | Secret | Pinecone index `learning` |
| `LEARNING_KG_NEO4J_*` | Secrets | Neo4j auth |
| `OPENAI_API_KEY` | Secret | Embeddings + router LLM |

Rotate the API token in `learning-kb-api-keys.txt` on the server, then re-run `sync-knowledge-base-gh-secrets.sh`.

---

## Repo map (what to read)

| File | Use |
|------|-----|
| [`AGENTS.md`](../AGENTS.md) | **Give this to your coding agent** — routing table, tools, boundaries |
| [`docs/routing.md`](routing.md) | Vector vs graph vs both — decision table |
| [`docs/public-api.md`](public-api.md) | HTTP API reference |
| [`docs/pinecone.md`](pinecone.md) | Vector index `learning` |
| [`docs/neo4j.md`](neo4j.md) | Graph `learning-kg-neo4j` |
| [`docs/agentic-router.md`](agentic-router.md) | Router architecture |
| [`llms.txt`](../llms.txt) | Machine discovery index |

---

## Corpus boundaries

**In scope:** James's learning corpus (course transcripts, patterns, langchain-docs namespace).  
**Out of scope:** Keyflo product SoT, VETRIQ/Townmark KBs, general web research.

**Access model:** READ ONLY — never write to Pinecone or Neo4j.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401` on `/v1/query` | Check `LEARNING_KB_API_TOKEN`; ask James for a new token |
| `429` | Rate limit (30/hr per token); wait or ask James to raise limit |
| `502` | Server-side router error; ping James |
| `/health` fails | API down — James: `sudo systemctl status learning-kb-api` |
| SSH CLI missing env | Ask James for read-only keys or server `load.sh` access |
| smoke-query workflow fails | Self-hosted runner `keyflo-server` not registered on this repo |

---

## External mirror

Same content, for clones outside the KeyFlo org:

`https://github.com/James-Server-Admin/keyflo-learning-kb`

Use the org repo when you have KeyFlo access.
