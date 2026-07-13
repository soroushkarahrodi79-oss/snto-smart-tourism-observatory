from __future__ import annotations

from src.config.settings import Settings


def test_database_url_defaults_to_sqlite() -> None:
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///data/outputs/snto.db"


def test_database_url_builds_postgres_when_host_set() -> None:
    settings = Settings(
        _env_file=None,
        snto_db_host="myhost",
        snto_db_user="u",
        snto_db_pass="p",
        snto_db_name="snto",
        snto_db_port=5432,
    )
    assert settings.database_url == "postgresql+psycopg2://u:p@myhost:5432/snto"


def test_database_url_explicit_override_wins() -> None:
    settings = Settings(
        _env_file=None,
        snto_db_host="myhost",
        snto_database_url="sqlite:///:memory:",
    )
    assert settings.database_url == "sqlite:///:memory:"
