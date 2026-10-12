"""Embeddings interface. Swappable: real model when available, else a
deterministic stub (clearly marked) so the API works end to end."""

import hashlib
import math
import os

DIM = int(os.environ.get("EMBEDDING_DIM", "384"))


class BaseEmbedder:
    name = "base"

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class HashEmbedder(BaseEmbedder):
    """Deterministic stub. NOT semantic — same text => same vector, but
    'dog' and 'puppy' are no closer than 'dog' and 'carburetor'.
    Only for dev until a real model is wired in."""

    name = "hash-stub"

    def embed(self, text: str) -> list[float]:
        vec = []
        for i in range(DIM):
            h = hashlib.sha256(f"{i}:{text}".encode()).digest()
            vec.append((int.from_bytes(h[:4], "big") / 2**32) * 2 - 1)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class FastEmbedder(BaseEmbedder):
    """Real semantic embeddings via fastembed (BAAI/bge-small-en-v1.5,
    384 dims, ONNX, CPU-friendly, no torch needed)."""

    name = "bge-small-en-v1.5"

    def __init__(self):
        from fastembed import TextEmbedding

        self.model = TextEmbedding("BAAI/bge-small-en-v1.5")

    def embed(self, text: str) -> list[float]:
        vec = list(self.model.embed([text]))[0]
        return [float(x) for x in vec]


class SentenceTransformerEmbedder(BaseEmbedder):
    """Real semantic embeddings via sentence-transformers (all-MiniLM-L6-v2,
    384 dims, ~90MB, runs on CPU)."""

    name = "all-MiniLM-L6-v2"

    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(self, text: str) -> list[float]:
        vec = self.model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vec]


def get_embedder() -> BaseEmbedder:
    which = os.environ.get("EMBEDDER", "fastembed")
    if which == "fastembed":
        try:
            return FastEmbedder()
        except Exception as e:
            print(f"[embeddings] fastembed unavailable ({e}); trying sentence-transformers")
    if which in ("fastembed", "st"):
        try:
            return SentenceTransformerEmbedder()
        except Exception as e:
            print(f"[embeddings] real model unavailable ({e}); using hash stub")
    return HashEmbedder()
