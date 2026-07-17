"""
Shared FastAPI dependencies for /api/v2 (Fase 5).

``require_write_auth`` is the single seam where write access — and "who is
writing" — enters the API. It is the real implementation of the ``get_actor``
seam introduced in step 5.7.

Auth model (step 5.8, ADR-011 — minimal built-in, gates writes only):

- ``settings.snto_api_key`` unset/empty → auth **disabled** (local/dev
  default, matching the rest of the persistence layer's permissive default).
  Writes stay open; the actor is best-effort from ``X-Actor`` (``anonymous``
  if absent) — exactly the pre-auth behaviour.
- ``settings.snto_api_key`` set → every write requires a matching
  ``X-API-Key`` header (constant-time compared); missing/invalid → ``401``.
  The actor is the ``X-Actor`` header, or ``api-key`` when the caller sends
  none.

Read endpoints never depend on this — reads are always open. SSO/Entra ID is
deferred to a future additive swap of this one dependency (ADR-011).
"""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from src.config.settings import settings


def require_write_auth(
    x_api_key: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
) -> str:
    """Gate a write endpoint; return the resolved actor for the audit trail."""
    configured = settings.snto_api_key
    if not configured:
        return x_actor or "anonymous"
    if not x_api_key or not hmac.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    return x_actor or "api-key"
