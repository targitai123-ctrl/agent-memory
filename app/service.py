"""Core memory operations shared by the API routes and the demo."""

from .auth import create_key, hash_key
from .db import get_conn
from .embeddings import get_embedder

embedder = get_embedder()
print(f"[memory] embedder: {embedder.name}")


def get_key(raw_key: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM api_keys WHERE key_hash = %s", (hash_key(raw_key),)
            )
            return cur.fetchone()


def touch_key(key_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE api_keys SET calls = calls + 1 WHERE id = %s", (key_id,))
            conn.commit()


def remember_text(key_id: int, text: str) -> int:
    vec = embedder.embed(text)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO memories (key_id, content, embedding) VALUES (%s, %s, %s) RETURNING id",
                (key_id, text, vec),
            )
            mid = cur.fetchone()["id"]
            conn.commit()
    return mid


def recall_text(key_id: int, query: str, limit: int = 5) -> list[dict]:
    vec = embedder.embed(query)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, created_at,
                       1 - (embedding <=> %s::vector) AS score
                FROM memories
                WHERE key_id = %s AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vec, key_id, vec, limit),
            )
            rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "text": r["content"],
            "score": round(float(r["score"]), 4),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


def list_memories(key_id: int, limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, content, created_at FROM memories WHERE key_id = %s ORDER BY id LIMIT %s",
                (key_id, limit),
            )
            rows = cur.fetchall()
    return [
        {"id": r["id"], "text": r["content"], "created_at": r["created_at"].isoformat()}
        for r in rows
    ]


def forget_memory(key_id: int, memory_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM memories WHERE id = %s AND key_id = %s",
                (memory_id, key_id),
            )
            conn.commit()
            return cur.rowcount > 0


def mint_key(name: str = "demo") -> str:
    return create_key(name)
