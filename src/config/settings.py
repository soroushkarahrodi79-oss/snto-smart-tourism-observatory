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

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
