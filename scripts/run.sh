#!/bin/bash
# Start the Agent Memory API (dev).
cd "$(dirname "$0")/.."
export DATABASE_URL="${DATABASE_URL:-postgresql://hatch:hatch@localhost/agent_memory}"
export HF_HUB_OFFLINE=1
export FASTEMBED_CACHE_PATH="${FASTEMBED_CACHE_PATH:-$HOME/workspace/.cache/fastembed}"
mkdir -p "$FASTEMBED_CACHE_PATH"
export no_proxy="localhost,127.0.0.1"
export NO_PROXY="localhost,127.0.0.1"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8420
