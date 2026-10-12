"""Database layer: Postgres + pgvector. Creates schema on startup."""

import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://localhost/agent_memory"
)
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL DEFAULT 'default',
    calls BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    key_id INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(%(dim)s),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS memories_key_idx ON memories(key_id);
""" % {"dim": EMBEDDING_DIM}


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            # vector similarity index (created once there's data to tune with;
            # plain scan is fine at MVP scale, index added when table grows)
            conn.commit()
