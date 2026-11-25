from __future__ import annotations

import sys

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

    # ── Auth mínima de escritura (Fase 5.8, ADR-011) ─────────────────────────
    # Vacío por defecto -> auth desactivada (dev local: las escrituras quedan
    # abiertas, igual que el resto de la capa por defecto). Rellenar activa el
    # gating: toda escritura /api/v2 exige la cabecera X-API-Key. La lectura
    # nunca se gatea. SSO/Entra ID queda diferido (swap aditivo, ver ADR-011).
    snto_api_key: str = ""

    # ── Demo pública de solo lectura ─────────────────────────────────────────
    # SNTO_PUBLIC_DEMO=true -> la conexión a la base se abre en solo lectura y
    # se rechaza toda escritura (UI, servicios, /api/v2, migraciones). Para
    # alojamientos públicos sin login (p. ej. Streamlit Community Cloud). Falso
    # por defecto: el uso local no cambia. Un valor no booleano en el entorno
    # impide el arranque (fail-closed). Consultar siempre is_public_demo().
    snto_public_demo: bool = False

    # ── Visual Change Explorer (ADR-015) ─────────────────────────────────────
    # Feature flag for the in-process Earth Engine Visual Change Explorer.
    # Falso por defecto -> el explorador queda desactivado y su punto de entrada
    # lanza EarthEngineDisabledError sin tocar Earth Engine. Poner a true (env
    # SNTO_ENABLE_CHANGE_EXPLORER=true) lo habilita; requiere además las
    # credenciales GEE_* (ver .env.example y docs/GEE_setup_timebox.md).
    snto_enable_change_explorer: bool = False

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


_FALSEY = {"false", "f", "0", "no", "n", "off"}


def _streamlit_secret_requests_public_demo() -> bool:
    """Read ``SNTO_PUBLIC_DEMO`` from Streamlit secrets, if Streamlit is running.

    Streamlit only copies str/int/float secrets into the environment, so an
    unquoted TOML ``SNTO_PUBLIC_DEMO = true`` would otherwise be silently
    ignored and leave the app writable.
    """
    st = sys.modules.get("streamlit")
    if st is None:
        return False
    try:
        if not st.secrets.load_if_toml_exists():
            return False
        if "SNTO_PUBLIC_DEMO" not in st.secrets:
            return False
        raw = st.secrets["SNTO_PUBLIC_DEMO"]
    except Exception:  # unreadable secrets file: fail closed
        return True
    # Anything that is not an explicit "off" counts as on.
    return str(raw).strip().lower() not in _FALSEY


def is_public_demo() -> bool:
    """True if either the environment or Streamlit secrets enable public demo mode.

    When the two sources disagree, read-only wins.
    """
    return settings.snto_public_demo or _streamlit_secret_requests_public_demo()
