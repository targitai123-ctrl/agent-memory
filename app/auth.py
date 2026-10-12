"""API key auth + per-key metering."""

import hashlib
import secrets

from fastapi import Header, HTTPException

from .db import get_conn


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_key(name: str = "default") -> str:
    raw = "am_" + secrets.token_urlsafe(32)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO api_keys (key_hash, name) VALUES (%s, %s) RETURNING id",
                (hash_key(raw), name),
            )
            conn.commit()
    return raw


def verify_key(x_api_key: str = Header(default="")) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="missing X-API-Key header")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM api_keys WHERE key_hash = %s", (hash_key(x_api_key),)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="invalid API key")
            cur.execute(
                "UPDATE api_keys SET calls = calls + 1 WHERE id = %s", (row["id"],)
            )
            conn.commit()
            return row
