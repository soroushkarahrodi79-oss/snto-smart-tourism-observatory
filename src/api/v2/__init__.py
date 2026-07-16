"""
Versioned API namespace for the persistent-backend resources (Fase 5, 5.3).

Additive and separate from the existing stateless routers
(``/evaluate_asset``, ``/ranking``, ``/alerts``), which keep their behavior
unchanged. Everything under ``/api/v2`` is backed by ``src.persistence`` and
is read-only in this step — write endpoints arrive gated by auth in step 5.8.
"""
