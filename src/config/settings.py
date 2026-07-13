from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    use_mock_data: bool = True

    gee_project_id: str = ""
    gee_service_account: str = ""
    gee_key_file: str = ""

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # ── Persistencia (Fase 5, ADR-011) ────────────────────────────────────────
    # Vacíos por defecto -> src.persistence.session cae a un fichero SQLite bajo
    # data/ (git-ignored). Rellenar SNTO_DB_HOST activa Postgres real; ningún
    # recurso de nube se aprovisiona por leer estas variables (ver ADR-011 §4bis
    # en docs/roadmap/plan_fase5_v2_foundations.md).
    snto_db_host: str = ""
    snto_db_port: int = 5432
    snto_db_name: str = "snto"
    snto_db_user: str = ""
    snto_db_pass: str = ""
    # Override explícito (p. ej. tests: "sqlite:///:memory:"); tiene prioridad
    # sobre snto_db_host/sqlite por defecto cuando se establece.
    snto_database_url: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def database_url(self) -> str:
        """URL de conexión SQLAlchemy: override explícito > Postgres > SQLite."""
        if self.snto_database_url:
            return self.snto_database_url
        if self.snto_db_host:
            return (
                f"postgresql+psycopg2://{self.snto_db_user}:{self.snto_db_pass}"
                f"@{self.snto_db_host}:{self.snto_db_port}/{self.snto_db_name}"
            )
        return "sqlite:///data/outputs/snto.db"


settings = Settings()
