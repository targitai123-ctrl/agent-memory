"""Agent Memory API — memory as a service for AI agents.

Endpoints:
  POST /v1/remember   {text}            -> {id}
  GET  /v1/recall?query=...&limit=5     -> [{id, text, score, created_at}]
  GET  /v1/memories                     -> [{id, text, created_at}]
  DELETE /v1/forget/{id}                -> {ok: true}
  GET  /v1/usage                        -> {calls}
  GET  /.well-known/service.json        -> machine-readable manifest
  GET  /demo                            -> interactive demo page
"""

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from . import service
from .auth import verify_key
from .db import get_conn, init_db
from .demo import router as demo_router

app = FastAPI(title="Agent Memory API", version="0.1.0")
app.include_router(demo_router)


class RememberIn(BaseModel):
    text: str


@app.on_event("startup")
def startup():
    init_db()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM api_keys")
            if cur.fetchone()["n"] == 0:
                from .auth import create_key

                key = create_key("dev")
                print(f"\n[memory] dev API key (save this): {key}\n")


@app.post("/v1/remember")
def remember(body: RememberIn, key: dict = Depends(verify_key)):
    service.touch_key(key["id"])
    return {"id": service.remember_text(key["id"], body.text)}


@app.get("/v1/recall")
def recall(query: str, limit: int = 5, key: dict = Depends(verify_key)):
    service.touch_key(key["id"])
    return service.recall_text(key["id"], query, limit)


@app.get("/v1/memories")
def memories(key: dict = Depends(verify_key)):
    service.touch_key(key["id"])
    return service.list_memories(key["id"])


@app.delete("/v1/forget/{memory_id}")
def forget(memory_id: int, key: dict = Depends(verify_key)):
    service.touch_key(key["id"])
    if not service.forget_memory(key["id"], memory_id):
        raise HTTPException(status_code=404, detail="memory not found")
    return {"ok": True}


@app.get("/v1/usage")
def usage(key: dict = Depends(verify_key)):
    service.touch_key(key["id"])
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT calls, name FROM api_keys WHERE id = %s", (key["id"],))
            row = cur.fetchone()
    return {"key_name": row["name"], "calls": row["calls"]}


@app.get("/.well-known/service.json")
def service_manifest():
    """Machine-readable manifest: this is what an AI agent reads
    instead of a landing page."""
    return {
        "name": "Agent Memory API",
        "version": "0.1.0",
        "description": "Long-term memory for AI agents: store facts, recall by meaning, forget on demand.",
        "endpoints": {
            "remember": {"method": "POST", "path": "/v1/remember", "body": {"text": "string"}},
            "recall": {"method": "GET", "path": "/v1/recall?query=...&limit=5"},
            "memories": {"method": "GET", "path": "/v1/memories"},
            "forget": {"method": "DELETE", "path": "/v1/forget/{id}"},
            "usage": {"method": "GET", "path": "/v1/usage"},
        },
        "auth": {"type": "api_key", "header": "X-API-Key"},
        "pricing": {"per_1k_calls_usd": 0.10, "free_tier_calls": 100000},
        "sla": {"uptime_target": "99.9%"},
    }


@app.get("/")
def root():
    return {
        "service": "Agent Memory API",
        "manifest": "/.well-known/service.json",
        "demo": "/demo",
        "docs": "/docs",
    }
