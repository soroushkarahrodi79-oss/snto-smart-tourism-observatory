from __future__ import annotations

import pytest

from src.config.settings import Settings

# Every key that can steer Settings.database_url. Cleared before every test in
# this file so no test's result depends on ambient os.environ (Phase 0.5A).
_DATABASE_ENV_KEYS = (
    "SNTO_DATABASE_URL",
    "SNTO_DB_HOST",
    "SNTO_DB_PORT",
    "SNTO_DB_NAME",
    "SNTO_DB_USER",
    "SNTO_DB_PASS",
)


def _clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _DATABASE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _assert_database_url_without_revealing(actual: str, expected: str) -> None:
    # Never compare with a raw `==` assertion here: pytest's assertion rewriter
    # would display both sides of a failing comparison, and `actual` may hold a
    # real connection string (including a password) if a future regression lets
    # ambient os.environ leak through. Fail without a value-revealing diff.
    if actual != expected:
        pytest.fail(
            "database_url did not match the expected configuration",
            pytrace=False,
        )


def test_database_url_defaults_to_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_database_environment(monkeypatch)

    settings = Settings(_env_file=None)

    _assert_database_url_without_revealing(
        settings.database_url, "sqlite:///data/outputs/snto.db"
    )


def test_database_url_builds_postgres_when_host_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_environment(monkeypatch)

    settings = Settings(
        _env_file=None,
        snto_db_host="myhost",
        snto_db_user="u",
        snto_db_pass="p",
        snto_db_name="snto",
        snto_db_port=5432,
    )

    _assert_database_url_without_revealing(
        settings.database_url, "postgresql+psycopg2://u:p@myhost:5432/snto"
    )


def test_database_url_explicit_override_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_environment(monkeypatch)

    settings = Settings(
        _env_file=None,
        snto_db_host="myhost",
        snto_database_url="sqlite:///:memory:",
    )

    _assert_database_url_without_revealing(settings.database_url, "sqlite:///:memory:")
