"""Interactive demo: chat with an agent that remembers you.

The 'aha' moment: tell it your name and a few facts, refresh the page
(or come back tomorrow) — it still knows you. Each visitor gets their
own API key = their own isolated memory namespace.
"""

import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import service

router = APIRouter()

FACT_PATTERNS = [
    (re.compile(r"my name is ([a-zA-Z'\-]{1,20}(?: [a-zA-Z'\-]{1,20})?)", re.I),
     lambda m: f"The user's name is {m.group(1).strip().title()}"),
    (re.compile(r"(?:i am|i'm) an? ([a-zA-Z' \-]{2,40})", re.I),
     lambda m: f"The user is a {m.group(1).strip()}"),
    (re.compile(r"i (?:like|love) ([a-zA-Z' \-]{2,60})", re.I),
     lambda m: f"The user likes {m.group(1).strip()}"),
    (re.compile(r"i (?:hate|dislike) ([a-zA-Z' \-]{2,60})", re.I),
     lambda m: f"The user dislikes {m.group(1).strip()}"),
    (re.compile(r"i own ([a-zA-Z0-9' .\-]{2,60})", re.I),
     lambda m: f"The user owns {m.group(1).strip()}"),
    (re.compile(r"my (store|shop|business|company|website|brand) is ([a-zA-Z0-9' .\-]{2,60})", re.I),
     lambda m: f"The user's {m.group(1).strip()} is {m.group(2).strip()}"),
    (re.compile(r"i live in ([a-zA-Z' \-]{2,40})", re.I),
     lambda m: f"The user lives in {m.group(1).strip().title()}"),
    (re.compile(r"i work as an? ([a-zA-Z' \-]{2,40})", re.I),
     lambda m: f"The user works as a {m.group(1).strip()}"),
]

REMEMBER_QUERIES = (
    "what do you remember",
    "what do you know about me",
    "do you remember me",
    "list memories",
    "show memories",
)


def extract_facts(message: str) -> list[str]:
    facts = []
    for pattern, fmt in FACT_PATTERNS:
        m = pattern.search(message)
        if m:
            facts.append(fmt(m))
    return facts


def get_name(key_id: int) -> str | None:
    top = service.recall_text(key_id, "the user's name", limit=1)
    if top and top[0]["score"] > 0.55 and top[0]["text"].startswith("The user's name is"):
        return top[0]["text"].split("is", 1)[1].strip()
    return None


def normalize(text: str) -> str:
    """Forgiving matching for chat shorthand."""
    t = text.lower()
    t = re.sub(r"\bu\b", "you", t)
    t = re.sub(r"\bur\b", "your", t)
    t = re.sub(r"\br\b", "are", t)
    return t


def handle_message(key_id: int, message: str) -> dict:
    service.touch_key(key_id)
    low = normalize(message.strip())

    if any(q in low for q in REMEMBER_QUERIES):
        mems = service.list_memories(key_id)
        if not mems:
            return {"reply": "Nothing yet — tell me something about yourself and I'll remember it.",
                    "stored": [], "recalled": []}
        lines = "\n".join("• " + m["text"] for m in mems)
        return {"reply": f"Here's everything I remember about you:\n{lines}",
                "stored": [], "recalled": [m["text"] for m in mems]}

    if low.rstrip("!") in ("hi", "hello", "hey", "yo", "sup", "hey there"):
        name = get_name(key_id)
        if name:
            return {"reply": f"Hey {name}! Good to see you again.", "stored": [], "recalled": []}
        return {"reply": "Hey! I don't think we've met — what's your name?",
                "stored": [], "recalled": []}

    stored = []
    for fact in extract_facts(message):
        top = service.recall_text(key_id, fact, limit=1)
        if not top or top[0]["score"] < 0.9:
            service.remember_text(key_id, fact)
            stored.append(fact)

    if stored:
        name_bit = ""
        for f in stored:
            if f.startswith("The user's name is"):
                name_bit = f" Nice to meet you, {f.split('is', 1)[1].strip()}."
                break
        return {"reply": f"Got it — I'll remember that.{name_bit}",
                "stored": stored, "recalled": []}

    # Bare-name reply: user answered "what's your name?" with just the name
    # (e.g. "Alan"). Only when we don't know a name yet and it looks like one.
    bare = message.strip()
    if get_name(key_id) is None and re.fullmatch(
        r"[A-Z][a-zA-Z'\-]{1,19}(?: [A-Z][a-zA-Z'\-]{1,19})?", bare
    ):
        fact = f"The user's name is {bare}"
        service.remember_text(key_id, fact)
        return {"reply": f"Nice to meet you, {bare}.",
                "stored": [fact], "recalled": []}

    recalled = service.recall_text(key_id, message, limit=3)
    good = [r for r in recalled if r["score"] > 0.5]
    if good and message.strip().endswith("?"):
        return {"reply": f"From what I remember: {good[0]['text']}",
                "stored": [], "recalled": [r["text"] for r in good]}
    if good:
        return {"reply": "Noted.", "stored": [], "recalled": [r["text"] for r in good]}
    return {"reply": "Tell me about yourself — your name, what you do, what you like. I remember everything.",
            "stored": [], "recalled": []}


class KeyOut(BaseModel):
    api_key: str


class ChatIn(BaseModel):
    api_key: str
    message: str


@router.post("/demo/key", response_model=KeyOut)
def demo_key():
    return {"api_key": service.mint_key("demo-visitor")}


@router.post("/demo/chat")
def demo_chat(body: ChatIn):
    from fastapi import HTTPException

    key = service.get_key(body.api_key)
    if not key:
        raise HTTPException(status_code=401, detail="invalid API key")
    result = handle_message(key["id"], body.message)
    result["memory_count"] = len(service.list_memories(key["id"]))
    return result


@router.get("/demo", response_class=HTMLResponse)
def demo_page():
    from pathlib import Path

    return (Path(__file__).parent / "demo_index.html").read_text()
