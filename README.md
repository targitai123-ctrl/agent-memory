# Agent Memory API

Long-term memory for AI agents, as a service. Three calls: **remember**, **recall**, **forget**.

Built agent-native: a machine-readable manifest at `/.well-known/service.json` lets an AI agent discover the endpoints, the auth scheme, and the price per call — and start using it with zero human integration work. The customer is the agent; the human just funds the account.

**Live demo:** http://143.110.216.91/demo — chat with an agent that remembers you across visits. Tell it your name, refresh the page, ask what it remembers.

## Quickstart

```bash
# 1. Environment setup: Postgres 16 + pgvector + database (idempotent)
./scripts/setup.sh

# 2. Install deps + run (first run prints a dev API key — save it)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./scripts/run.sh
```

## Use it

```bash
KEY="am_your_key_here"
BASE="http://localhost:8420"

# Remember a fact
curl -X POST $BASE/v1/remember -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"The user wears size large and hates polyester"}'
# -> {"id": 1}

# Recall by meaning (not keywords)
curl "$BASE/v1/recall?query=clothing+preferences&limit=3" -H "X-API-Key: $KEY"
# -> [{"id":1, "text":"The user wears size large...", "score":0.71, ...}]

# Forget
curl -X DELETE $BASE/v1/forget/1 -H "X-API-Key: $KEY"
# -> {"ok": true}

# Usage metering (this is what billing reads)
curl $BASE/v1/usage -H "X-API-Key: $KEY"
# -> {"key_name":"dev","calls":42}
```

## For AI agents

```
GET /.well-known/service.json
```

One file describes every endpoint, the auth scheme, and pricing. An agent reads it and self-configures — no SDK, no docs site, no human clicks.

## How it works

- **API:** FastAPI (Python)
- **Storage + vector search:** Postgres 16 + pgvector — one database does both
- **Embeddings:** `BAAI/bge-small-en-v1.5` via fastembed (384 dims, ONNX, CPU-friendly, no torch). Set `EMBEDDER=stub` for the deterministic hash stub (dev only — not semantic)
- **Auth:** API keys stored as SHA-256 hashes, strict per-key memory isolation
- **Metering:** every authenticated call increments the key's counter

```
app/
  main.py        # routes: remember / recall / memories / forget / usage / manifest / demo
  service.py     # core memory operations
  db.py          # Postgres + pgvector schema
  auth.py        # key issue / verify / metering
  embeddings.py  # swappable embedder
  demo.py        # interactive demo backend (+ demo_index.html)
scripts/
  setup.sh       # one-command env setup (idempotent)
  run.sh         # start the API
```

## Roadmap

- [ ] Memory decay (old memories fade unless reinforced)
- [ ] Conflict resolution ("user said X, then Y — which is true?")
- [ ] Stripe billing (human funds the account, agent spends it)
- [ ] x402 per-call payments from agent wallets
- [ ] Agent service registry listings

## License

MIT — use it for anything.
