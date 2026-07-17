"""
Shared FastAPI dependencies for /api/v2 (Fase 5).

``get_actor`` is the single seam where "who is writing" enters the API. Auth
does not exist yet (step 5.8): for now the actor is read from an optional
``X-Actor`` header and defaults to ``anonymous``. When 5.8 lands, this
dependency is the only thing that changes — it will derive the actor from the
authenticated principal instead of a header — and every write endpoint keeps
depending on it unchanged.
"""
from __future__ import annotations

from fastapi import Header


def get_actor(x_actor: str | None = Header(default=None)) -> str:
    return x_actor or "anonymous"
