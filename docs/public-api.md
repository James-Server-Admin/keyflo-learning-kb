# Public HTTP query API

Read-only gateway to the learning corpus agentic router. Runs on the Keyflo server; expose via Cloudflare + nginx (TLS at the edge).

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | none | Liveness check |
| `POST` | `/v1/query` | Bearer token | Route + answer from Pinecone/Neo4j |

### `POST /v1/query`

```json
{
  "question": "which courses cover copywriting?",
  "k": 6,
  "max_retries": 2
}
```

Response:

```json
{
  "answer": "...",
  "route": "graph",
  "route_reason": "...",
  "graph_context": "...",
  "source_documents": ["..."],
  "retries": 0
}
```

Limits (env-configurable):

- `k`: 1–12 (default 6)
- Question max length: 4000 chars
- Rate limit: 30 requests/hour per API key (in-memory, single process)

## Authentication

Bearer tokens live in `/mnt/blockstorage/private/credentials/learning-kb-api-keys.txt` (one hex token per line, mode 600). Reference via:

```bash
export LEARNING_KB_API_KEYS_PATH=/mnt/blockstorage/private/credentials/learning-kb-api-keys.txt
```

Optional comma-separated override: `LEARNING_KB_API_KEYS` (avoid in production — prefer file).

**Give Cole a token out of band** (1Password, Signal, etc.). Never commit tokens or paste in GitHub.

Example:

```bash
curl -s https://kb-api.keyflo.ai/v1/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"how do I structure a Meta lead gen campaign?","k":6}'
```

## Run locally (server)

```bash
cd /mnt/blockstorage/business/Keyflo_AI/08_Development/knowledge-base
source /mnt/blockstorage/env/load.sh
./scripts/run-api.sh
# listens 127.0.0.1:8791 by default
curl -s http://127.0.0.1:8791/health
```

### systemd

```bash
sudo cp deploy/learning-kb-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now learning-kb-api
sudo systemctl status learning-kb-api
```

## Edge exposure (Cloudflare + nginx)

**Pattern:** TLS and WAF at Cloudflare; nginx on the server terminates proxy to localhost API.

1. **DNS** (`keyflo` profile): `kb-api.keyflo.ai` → A record → `192.241.169.31`, proxied orange-cloud OK for WAF.
2. **nginx** (see `deploy/nginx-kb-api.conf`): reverse proxy to `127.0.0.1:8791` on **both port 80 and 443** (Cloudflare Full SSL hits origin :443). Use Cloudflare origin cert `*.keyflo.ai`. Include `listen [::]:443 ssl` so IPv6 origin connections match this vhost.
3. **Cloudflare:** rate limiting rule on `/v1/query`, bot fight mode optional, restrict countries if needed.
4. **Do not** bind the API to `0.0.0.0` without nginx + auth — always use bearer tokens.

Regenerate a token:

```bash
echo "# label-$(date +%Y-%m)" >> /mnt/blockstorage/private/credentials/learning-kb-api-keys.txt
openssl rand -hex 32 >> /mnt/blockstorage/private/credentials/learning-kb-api-keys.txt
chmod 600 /mnt/blockstorage/private/credentials/learning-kb-api-keys.txt
sudo systemctl restart learning-kb-api
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LEARNING_KB_API_HOST` | `127.0.0.1` | Bind address |
| `LEARNING_KB_API_PORT` | `8791` | Port |
| `LEARNING_KB_API_KEYS_PATH` | `.../learning-kb-api-keys.txt` | Bearer tokens file |
| `LEARNING_KB_API_RATE_LIMIT_PER_HOUR` | `30` | Per-key limit |
| `LANGCHAIN_COURSE_REPO` | `/root/langchain-course` | Router runtime |
| `LEARNING_*`, `OPENAI_API_KEY` | from `global.env` | Pinecone, Neo4j, LLM |

## Cole handoff (no SSH)

1. James sends a bearer token securely.
2. Cole copies `config/cole.env.example` → `config/cole.env`, sets `LEARNING_KB_API_TOKEN`.
3. Run queries: `python scripts/query_api.py "your question"` or curl below.
4. Full checklist: [`docs/COLE-SETUP.md`](COLE-SETUP.md)

```bash
python scripts/query_api.py "which courses cover copywriting?"
```
