# Public HTTP query API

Read-only HTTP fallback for James's learning corpus. By default it runs
full-corpus `query_all`; set `all_namespaces=false` to use the graph/vector
agentic router. Runs on the server; expose via Cloudflare + nginx (TLS at the
edge).

For MCP-capable agents, prefer the canonical `kb-gateway` MCP tool
`answer_learning_kb` at `https://kb-mcp.waytie.com/mcp`. Use this HTTP API for
scripts, no-MCP agents, browser/mobile wrappers, or simple single-shot Q&A.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | none | Liveness check |
| `POST` | `/v1/query` | Bearer token | Default full-corpus answer from Pinecone; optional router answer from Pinecone/Neo4j |

This endpoint does not expose raw Pinecone or Neo4j credentials. Agents should
cite returned `source_documents` and should not make absence claims from one
empty or errored response.

### `POST /v1/query`

```json
{
  "question": "which courses cover copywriting?",
  "k": 6,
  "max_retries": 2,
  "all_namespaces": true
}
```

Default response (`all_namespaces=true`):

```json
{
  "answer": "...",
  "namespaces": ["course-transcripts", "patterns", "research-papers"],
  "per_namespace_counts": {"course-transcripts": 6, "patterns": 2},
  "source_documents": ["..."]
}
```

Router response (`all_namespaces=false`):

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

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `local HTTP 200`, public `403` or HTML error (not JSON) | Cloudflare **Full SSL** hits origin on **443** but nginx had no `kb-api.keyflo.ai` TLS vhost | Deploy `deploy/nginx-kb-api.conf` (port **443** + `[::]:443`, origin cert), `nginx -t && systemctl reload nginx` |
| Public `401` + `missing or invalid Authorization` | No `Authorization: Bearer` header | Send bearer token on every `/v1/query` request |
| Public `401` + `invalid api key` | Token not in `learning-kb-api-keys.txt` | Add token to keys file, `systemctl restart learning-kb-api`; sync Cole via `sync-knowledge-base-gh-secrets.sh` |
| Public `403` / Cloudflare **Error 1010** (autonomous system) | WAF / bot rules blocking API clients | Cloudflare dashboard → **Security** → **WAF** → custom rule: if `http.host eq "kb-api.keyflo.ai"` and path starts with `/v1/` and `Authorization` header present → **Skip** remaining rules. Use a token with WAF edit permission if automating via API. |
| `GET /health` **200**, `POST /v1/query` fails | Usually auth or nginx not forwarding `/v1/` | Confirm `proxy_set_header Authorization $http_authorization;` on `/v1/` locations |

Quick checks (do not paste tokens in tickets):

```bash
curl -s -w "health %{http_code}\n" https://kb-api.keyflo.ai/health
curl -s -o /dev/null -w "local %{http_code}\n" -H "Authorization: Bearer $LEARNING_KB_API_TOKEN" \
  -H "Content-Type: application/json" -d '{"question":"test","k":2}' http://127.0.0.1:8791/v1/query
curl -s -o /dev/null -w "public %{http_code}\n" -H "Authorization: Bearer $LEARNING_KB_API_TOKEN" \
  -H "Content-Type: application/json" -d '{"question":"test","k":2}' https://kb-api.keyflo.ai/v1/query
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
