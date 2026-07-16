"""
Service layer bridging the in-memory analytical core to persistence
(Fase 5, step 5.4+).

Repositories (``src/persistence/repositories/``) do typed CRUD on single
resources; services orchestrate across several of them and translate the
domain objects produced by ``src.alerts`` / ``src.risk_engine`` into persisted
records.
"""
